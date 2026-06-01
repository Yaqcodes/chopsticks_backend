"""Apply OAuth provider profile fields to User records."""

import logging

logger = logging.getLogger(__name__)


def normalize_oauth_names(first_name='', last_name='', full_name=''):
    """
    Normalize given/family names from Google (or similar).
    Uses full ``name`` when given_name is missing.
    """
    first_name = (first_name or '').strip()
    last_name = (last_name or '').strip()
    full_name = (full_name or '').strip()

    if not first_name and full_name:
        parts = full_name.split(None, 1)
        first_name = parts[0] if parts else ''
        if not last_name and len(parts) > 1:
            last_name = parts[1]

    return first_name, last_name


def sync_user_profile_from_oauth(user, *, first_name='', last_name=''):
    """
    Persist OAuth names on the user when local fields are empty.
    Does not overwrite names the user already set.
    """
    first_name, last_name = normalize_oauth_names(first_name, last_name)

    update_fields = []
    if first_name and not (user.first_name or '').strip():
        user.first_name = first_name
        update_fields.append('first_name')
    if last_name and not (user.last_name or '').strip():
        user.last_name = last_name
        update_fields.append('last_name')

    if update_fields:
        user.save(update_fields=update_fields)
        logger.info(
            'Updated OAuth profile fields for user %s: %s',
            user.pk,
            ', '.join(update_fields),
        )


def apply_google_profile_to_user(user, google_user_info):
    """Apply normalized Google profile to an existing or newly created user."""
    first_name, last_name = normalize_oauth_names(
        google_user_info.get('first_name', ''),
        google_user_info.get('last_name', ''),
        google_user_info.get('full_name', ''),
    )
    sync_user_profile_from_oauth(user, first_name=first_name, last_name=last_name)
