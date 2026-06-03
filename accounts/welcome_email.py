import logging

logger = logging.getLogger(__name__)


def schedule_welcome_email_for_new_user(user, restaurant_settings):
    """
    Enqueue welcome email after commit for newly created accounts only.

    Used by email/password registration and first-time OAuth sign-up.
    """
    if not user or not restaurant_settings:
        return
    try:
        from utils.tasks import enqueue_after_commit, send_welcome_task

        enqueue_after_commit(send_welcome_task, user.id, restaurant_settings.id)
    except Exception as exc:
        logger.warning('Welcome email skipped: %s', exc)
