"""Audit helpers for Product ↔ MenuItem (variant) linking."""

from core.utils import get_business_from_request

from .models import ProductVariantLinkEvent


def log_product_variant_link(
    request,
    *,
    action,
    product_id,
    menu_item_id,
    previous_product_id=None,
    restaurant_settings=None,
):
    """
    Persist link/unlink to ProductVariantLinkEvent.

    ``restaurant_settings`` overrides tenant resolution (e.g. Zmall admin may not
    send the storefront Origin header).
    """
    rs = restaurant_settings or get_business_from_request(request)
    if rs is None:
        return

    user = getattr(request, 'user', None)
    acting_user = user if getattr(user, 'is_authenticated', False) else None

    ProductVariantLinkEvent.objects.create(
        restaurant_settings=rs,
        acting_user=acting_user,
        action=str(action)[:20],
        product_id=product_id,
        menu_item_id=menu_item_id,
        previous_product_id=previous_product_id,
    )

