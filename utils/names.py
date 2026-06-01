"""Name helpers for customer-facing messages."""


def first_name_from_display_name(name: str) -> str:
    """Return the first token of a display or full name."""
    if not name:
        return ''
    parts = str(name).strip().split()
    return parts[0] if parts else ''


def get_user_first_name(user) -> str:
    """
    First name for greetings. Never derives from email — use username or blank.
    """
    if not user:
        return ''
    first = (getattr(user, 'first_name', None) or '').strip()
    if first:
        return first
    from_full = first_name_from_display_name(getattr(user, 'full_name', '') or '')
    if from_full:
        return from_full
    username = (getattr(user, 'username', None) or '').strip()
    if username:
        return first_name_from_display_name(username)
    return ''


def get_order_customer_first_name(order) -> str:
    """First name for order emails; guest orders use guest_name only (not email)."""
    if order.user:
        name = get_user_first_name(order.user)
        if name:
            return name
    return first_name_from_display_name(order.guest_name or '')


def greeting_name_for_user(user, *, default='there') -> str:
    return get_user_first_name(user) or default


def greeting_name_for_order(order, *, default='there') -> str:
    return get_order_customer_first_name(order) or default
