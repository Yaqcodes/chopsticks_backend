import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.media_urls import absolute_media_url
from core.utils import get_frontend_url_from_business, get_order_frontend_url
from utils.names import greeting_name_for_order, greeting_name_for_user
from utils.tenant_branding import get_tenant_display_name

logger = logging.getLogger(__name__)


def _build_from_email(restaurant_settings):
    return f'{get_tenant_display_name(restaurant_settings)} <{settings.DEFAULT_FROM_EMAIL}>'


def _greeting_name_for_user(user):
    return greeting_name_for_user(user)


def _base_email_context(restaurant_settings, request=None, *, greeting_name=None):
    logo_url = absolute_media_url(restaurant_settings.logo) if restaurant_settings.logo else None
    try:
        frontend_url = get_frontend_url_from_business(restaurant_settings, request=request)
    except ValueError:
        frontend_url = restaurant_settings.website or ''
    brand_name = get_tenant_display_name(restaurant_settings)
    return {
        'business': restaurant_settings,
        'business_name': brand_name,
        'greeting_name': greeting_name or 'there',
        'logo_url': logo_url,
        'frontend_url': frontend_url.rstrip('/') if frontend_url else '',
        'support_email': restaurant_settings.email or '',
        'support_phone': restaurant_settings.phone or '',
    }


def send_templated_email(
    *,
    restaurant_settings,
    to,
    subject,
    template_name,
    context=None,
    request=None,
    greeting_name=None,
):
    """Send HTML + plain-text email with tenant branding."""
    if not to:
        logger.warning('send_templated_email: no recipient for subject=%s', subject)
        return False

    recipient_list = [to] if isinstance(to, str) else list(to)
    recipient_list = [addr for addr in recipient_list if addr]
    if not recipient_list:
        return False

    email_context = {
        **_base_email_context(
            restaurant_settings,
            request=request,
            greeting_name=greeting_name,
        ),
        **(context or {}),
    }
    html_message = render_to_string(f'emails/{template_name}.html', email_context)
    plain_message = strip_tags(html_message)

    headers = {}
    if restaurant_settings.email:
        headers['Reply-To'] = restaurant_settings.email

    try:
        kwargs = {}
        if headers:
            kwargs['headers'] = headers
        message = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=_build_from_email(restaurant_settings),
            to=recipient_list,
            **kwargs,
        )
        message.attach_alternative(html_message, 'text/html')
        message.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception(
            'Failed to send email template=%s to=%s: %s',
            template_name,
            recipient_list,
            exc,
        )
        return False


def send_order_confirmation_email(order, request=None):
    subject = f'Order Confirmation - {order.order_number}'
    greeting = greeting_name_for_order(order)
    context = {
        'order': order,
        'order_number': order.order_number,
        'order_url': get_order_frontend_url(order, request=request),
        'total_amount': order.total_amount,
        'delivery_address': order.delivery_address or 'No address provided',
        'delivery_type': order.get_delivery_type_display(),
        'items': list(order.items.select_related('menu_item').all()),
    }
    return send_templated_email(
        restaurant_settings=order.restaurant_settings,
        to=order.get_customer_email(),
        subject=subject,
        template_name='order_confirmation',
        context=context,
        greeting_name=greeting,
    )


def send_order_status_update_email(order, new_status, request=None):
    status_display = dict(order.STATUS_CHOICES).get(new_status, new_status)
    subject = f'Order Update - {order.order_number}'
    greeting = greeting_name_for_order(order)
    context = {
        'order': order,
        'order_number': order.order_number,
        'order_url': get_order_frontend_url(order, request=request),
        'new_status': new_status,
        'status_display': status_display,
    }
    return send_templated_email(
        restaurant_settings=order.restaurant_settings,
        to=order.get_customer_email(),
        subject=subject,
        template_name='order_status_update',
        context=context,
        greeting_name=greeting,
    )


def send_password_reset_email(user, restaurant_settings, reset_url, request=None):
    brand = get_tenant_display_name(restaurant_settings)
    subject = f'Password Reset - {brand}'
    return send_templated_email(
        restaurant_settings=restaurant_settings,
        to=user.email,
        subject=subject,
        template_name='password_reset',
        context={
            'user': user,
            'reset_url': reset_url,
            'expiry_hours': 24,
        },
        request=request,
        greeting_name=_greeting_name_for_user(user),
    )


def send_welcome_email(user, restaurant_settings, request=None):
    brand = get_tenant_display_name(restaurant_settings)
    subject = f'Welcome to {brand}!'
    return send_templated_email(
        restaurant_settings=restaurant_settings,
        to=user.email,
        subject=subject,
        template_name='welcome',
        context={
            'user': user,
            'referral_code': user.referral_code,
        },
        request=request,
        greeting_name=_greeting_name_for_user(user),
    )


def send_points_earned_email(user, restaurant_settings, points_earned, reason):
    from loyalty.models import UserPoints

    total_points = 0
    try:
        user_points = UserPoints.objects.get(
            user=user,
            restaurant_settings=restaurant_settings,
        )
        total_points = user_points.balance
    except UserPoints.DoesNotExist:
        pass

    subject = f'You earned {points_earned} points!'
    return send_templated_email(
        restaurant_settings=restaurant_settings,
        to=user.email,
        subject=subject,
        template_name='points_earned',
        context={
            'user': user,
            'points_earned': points_earned,
            'reason': reason,
            'total_points': total_points,
        },
        greeting_name=_greeting_name_for_user(user),
    )


def send_reward_redemption_email(user, restaurant_settings, reward, points_spent):
    subject = f'Reward Redeemed: {reward.name}'
    return send_templated_email(
        restaurant_settings=restaurant_settings,
        to=user.email,
        subject=subject,
        template_name='reward_redemption',
        context={
            'user': user,
            'reward': reward,
            'points_spent': points_spent,
        },
        greeting_name=_greeting_name_for_user(user),
    )
