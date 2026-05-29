"""Shared promo code validation and usage recording."""

from decimal import Decimal

from .models import PromoCode, PromoCodeUsage


class PromoCodeError(Exception):
    """Raised when a promo code cannot be applied."""

    def __init__(self, message, code='invalid'):
        self.message = message
        self.code = code
        super().__init__(message)


def normalize_promo_code(code):
    """Return uppercase stripped code or None if empty."""
    if code is None:
        return None
    normalized = str(code).strip().upper()
    return normalized or None


def resolve_promo_code(code, restaurant_settings):
    """Look up a promo code for the given business."""
    normalized = normalize_promo_code(code)
    if not normalized:
        return None
    try:
        return PromoCode.objects.get(
            code=normalized,
            restaurant_settings=restaurant_settings,
        )
    except PromoCode.DoesNotExist as exc:
        raise PromoCodeError('Invalid promotional code.', 'not_found') from exc


def validate_promo_for_checkout(
    code,
    order_amount,
    restaurant_settings,
    user=None,
    guest_email=None,
    require_auth=True,
):
    """
    Validate a promo code and return (promo_code, discount_amount).

    order_amount is typically the cart subtotal (before tax and delivery).
    """
    if require_auth and (not user or not getattr(user, 'is_authenticated', False)):
        raise PromoCodeError('Log in to use a promo code.', 'auth_required')

    promo = resolve_promo_code(code, restaurant_settings)
    if promo is None:
        raise PromoCodeError('Promotional code is required.', 'required')

    if not promo.is_valid:
        raise PromoCodeError('This promotional code is not currently valid.', 'expired')

    if promo.customer_usage_limit_reached(user=user, guest_email=guest_email):
        if promo.usage_limit == 1:
            message = 'You have already used this promotional code.'
        else:
            message = f'You have reached the limit of {promo.usage_limit} uses for this promotional code.'
        raise PromoCodeError(message, 'usage_limit_reached')

    if not promo.is_valid_for_customer(user=user, guest_email=guest_email):
        raise PromoCodeError('This promotional code is not valid for you.', 'invalid_for_customer')

    order_amount = Decimal(str(order_amount))
    if order_amount < promo.minimum_order_amount:
        raise PromoCodeError(
            f'Minimum order amount of ₦{promo.minimum_order_amount:.2f} required for this code.',
            'minimum_not_met',
        )

    discount = promo.calculate_discount(order_amount)
    if discount <= 0:
        raise PromoCodeError('This promotional code does not apply to this order.', 'no_discount')

    return promo, discount


def record_promo_usage(promo_code, order, discount_amount, user=None, guest_email=None):
    """Create a usage record and increment global usage count."""
    normalized_email = ''
    if guest_email:
        normalized_email = guest_email.strip().lower()

    PromoCodeUsage.objects.create(
        promo_code=promo_code,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
        guest_email=normalized_email,
        order=order,
        discount_amount=discount_amount,
    )
