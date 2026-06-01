import logging
from functools import partial

from celery import shared_task
from django.db import OperationalError, transaction

logger = logging.getLogger(__name__)


def enqueue_after_commit(task, *args, **kwargs):
    """Schedule a Celery task only after the current DB transaction commits."""

    def _dispatch():
        try:
            task.delay(*args, **kwargs)
        except Exception:
            logger.exception(
                'Post-commit task failed to run: %s',
                getattr(task, 'name', task),
            )

    transaction.on_commit(_dispatch)


def schedule_order_status_update_email(order_id, new_status):
    """Enqueue a status-update email after the current transaction commits."""
    enqueue_after_commit(send_order_status_update_task, order_id, new_status)


def schedule_order_status_update_emails(pending):
    """
    Enqueue status-update emails for many orders after commit (e.g. admin bulk actions).

    pending: iterable of (order_id, new_status) pairs.
    """
    items = list(pending)
    if not items:
        return

    def _dispatch_all():
        for order_id, new_status in items:
            try:
                send_order_status_update_task.delay(order_id, new_status)
            except Exception:
                logger.exception(
                    'Post-commit status email failed for order %s',
                    order_id,
                )

    transaction.on_commit(_dispatch_all)


def schedule_order_confirmation_email(order_id):
    """
    Enqueue confirmation email after commit.

    Idempotency: skip if already sent; the worker uses select_for_update +
    confirmation_email_sent_at so duplicate tasks from callback + verify are safe.

    Do not pass a fixed Celery task_id — a failed send still reserves that id and
    blocks retries on later payment webhooks.
    """
    from orders.models import Order

    if Order.objects.filter(pk=order_id, confirmation_email_sent_at__isnull=False).exists():
        return

    def _dispatch():
        try:
            send_order_confirmation_task.delay(order_id)
        except Exception:
            logger.exception(
                'Failed to enqueue confirmation email for order %s',
                order_id,
            )

    transaction.on_commit(_dispatch)


def schedule_points_earned_email(user, restaurant_settings, points, reason):
    """Enqueue points-earned email when the user has an email address."""
    from django.conf import settings

    if not getattr(settings, 'POINTS_EARNED_EMAILS_ENABLED', False):
        return
    if not user or not getattr(user, 'email', None) or not points or points <= 0:
        return
    enqueue_after_commit(
        send_points_earned_task,
        user.id,
        restaurant_settings.id,
        int(points),
        reason,
    )


@shared_task(
    name='utils.send_order_confirmation_task',
    queue='email',
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def send_order_confirmation_task(order_id):
    from django.utils import timezone

    from orders.models import Order
    from utils.email import send_order_confirmation_email

    try:
        with transaction.atomic():
            # Do not combine select_for_update with prefetch_related on Postgres
            # (FOR UPDATE cannot be applied to the nullable side of an outer join).
            order = Order.objects.select_for_update().select_related(
                'restaurant_settings',
                'user',
            ).get(pk=order_id)

            if order.confirmation_email_sent_at:
                return 'already_sent'
            if order.payment_status != 'paid':
                return 'not_paid'

            recipient = order.get_customer_email()
            if not recipient:
                logger.warning('Order %s has no customer email', order_id)
                return 'no_recipient'

            item_count = order.items.count()
            if item_count == 0:
                logger.error(
                    'Order %s has no line items; skipping confirmation email (will retry)',
                    order_id,
                )
                return 'no_items'

            if not send_order_confirmation_email(order):
                return 'send_failed'

            order.confirmation_email_sent_at = timezone.now()
            order.save(update_fields=['confirmation_email_sent_at'])
            return 'sent'
    except Order.DoesNotExist:
        logger.error('send_order_confirmation_task: order %s not found', order_id)
        return 'not_found'
    except OperationalError:
        raise
    except Exception as exc:
        logger.exception('send_order_confirmation_task failed for order %s: %s', order_id, exc)
        return 'error'


@shared_task(name='utils.send_order_status_update_task', queue='email')
def send_order_status_update_task(order_id, new_status):
    from orders.models import Order
    from utils.email import send_order_status_update_email

    try:
        order = Order.objects.select_related('restaurant_settings', 'user').get(pk=order_id)
        if not order.get_customer_email():
            return 'no_recipient'
        # Use new_status from the task args (not order.status) so emails still send
        # if the order was changed again before the task ran.
        if send_order_status_update_email(order, new_status):
            return 'sent'
        return 'send_failed'
    except Order.DoesNotExist:
        logger.error('send_order_status_update_task: order %s not found', order_id)
        return 'not_found'
    except Exception as exc:
        logger.exception(
            'send_order_status_update_task failed for order %s: %s',
            order_id,
            exc,
        )
        return 'error'


@shared_task(name='utils.send_password_reset_task', queue='email')
def send_password_reset_task(user_id, restaurant_settings_id, reset_url):
    from accounts.models import User
    from core.models import RestaurantSettings
    from utils.email import send_password_reset_email

    try:
        user = User.objects.get(pk=user_id)
        restaurant_settings = RestaurantSettings.objects.get(pk=restaurant_settings_id)
        if send_password_reset_email(user, restaurant_settings, reset_url):
            return 'sent'
        return 'send_failed'
    except (User.DoesNotExist, RestaurantSettings.DoesNotExist) as exc:
        logger.error('send_password_reset_task: %s', exc)
        return 'not_found'
    except Exception as exc:
        logger.exception('send_password_reset_task failed: %s', exc)
        raise


@shared_task(name='utils.send_welcome_task', queue='email')
def send_welcome_task(user_id, restaurant_settings_id):
    from accounts.models import User
    from core.models import RestaurantSettings
    from utils.email import send_welcome_email

    try:
        user = User.objects.get(pk=user_id)
        restaurant_settings = RestaurantSettings.objects.get(pk=restaurant_settings_id)
        if send_welcome_email(user, restaurant_settings):
            return 'sent'
        return 'send_failed'
    except (User.DoesNotExist, RestaurantSettings.DoesNotExist) as exc:
        logger.error('send_welcome_task: %s', exc)
        return 'not_found'
    except Exception as exc:
        logger.exception('send_welcome_task failed: %s', exc)
        raise


@shared_task(name='utils.send_points_earned_task', queue='email')
def send_points_earned_task(user_id, restaurant_settings_id, points, reason):
    from accounts.models import User
    from core.models import RestaurantSettings
    from utils.email import send_points_earned_email

    try:
        user = User.objects.get(pk=user_id)
        restaurant_settings = RestaurantSettings.objects.get(pk=restaurant_settings_id)
        if points <= 0:
            return 'skipped'
        if send_points_earned_email(user, restaurant_settings, points, reason):
            return 'sent'
        return 'send_failed'
    except (User.DoesNotExist, RestaurantSettings.DoesNotExist) as exc:
        logger.error('send_points_earned_task: %s', exc)
        return 'not_found'
    except Exception as exc:
        logger.exception('send_points_earned_task failed: %s', exc)
        raise


@shared_task(name='utils.send_reward_redemption_task', queue='email')
def send_reward_redemption_task(user_id, restaurant_settings_id, reward_id, points_spent):
    from accounts.models import User
    from core.models import RestaurantSettings
    from loyalty.models import Reward
    from utils.email import send_reward_redemption_email

    try:
        user = User.objects.get(pk=user_id)
        restaurant_settings = RestaurantSettings.objects.get(pk=restaurant_settings_id)
        reward = Reward.objects.get(pk=reward_id, restaurant_settings=restaurant_settings)
        if send_reward_redemption_email(user, restaurant_settings, reward, points_spent):
            return 'sent'
        return 'send_failed'
    except (User.DoesNotExist, RestaurantSettings.DoesNotExist, Reward.DoesNotExist) as exc:
        logger.error('send_reward_redemption_task: %s', exc)
        return 'not_found'
    except Exception as exc:
        logger.exception('send_reward_redemption_task failed: %s', exc)
        raise
