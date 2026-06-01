"""Name helpers for customer-facing messages."""


def first_name_from_display_name(name: str) -> str:
    """Return the first token of a display or full name."""
    if not name:
        return ''
    parts = str(name).strip().split()
    return parts[0] if parts else ''


def get_user_first_name(user) -> str:
    if not user:
        return ''
    first = (getattr(user, 'first_name', None) or '').strip()
    if first:
        return first
    return first_name_from_display_name(getattr(user, 'full_name', '') or '')


def get_order_customer_first_name(order) -> str:
    if order.user:
        name = get_user_first_name(order.user)
        if name:
            return name
    return first_name_from_display_name(order.guest_name or '')
