"""Tenant display names for email and customer-facing copy."""

ZMALL_DISPLAY_NAME = 'Zmall Online Store'


def is_zmall_tenant(restaurant_settings) -> bool:
    if not restaurant_settings:
        return False
    domain = (restaurant_settings.domain or '').lower()
    name = (restaurant_settings.name or '').lower()
    return 'zmall' in domain or 'zmall' in name.replace(' ', '')


def normalize_brand_casing(name: str) -> str:
    """Ensure Zmall branding never appears as ZMall in customer-facing text."""
    if not name:
        return name
    normalized = name.replace('ZMall', 'Zmall').replace('Z Mall', 'Zmall')
    return normalized


def get_tenant_display_name(restaurant_settings) -> str:
    """Sender name, email header title, and subjects for a tenant."""
    if is_zmall_tenant(restaurant_settings):
        return ZMALL_DISPLAY_NAME
    return normalize_brand_casing((restaurant_settings.name or '').strip()) or 'Store'
