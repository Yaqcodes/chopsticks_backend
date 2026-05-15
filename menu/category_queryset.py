"""Storefront category list helpers (nav, category tabs)."""

from django.db.models import Exists, OuterRef, Q

from core.models import CatalogListingMode

from .models import Category, MenuItem, Product


def exclude_placeholder_categories(queryset):
    """Hide the catch-all bucket for unsorted menu items."""
    return queryset.exclude(name__iexact='None').exclude(slug__iexact='none')


def _normalize_gender_param(gender):
    if gender is None:
        return None
    g = str(gender).strip().lower()
    if g in ('', 'all'):
        return None
    return g


def _category_nav_audience_q(nav_gender):
    """Which categories appear in Men/Women nav for a shopper tab."""
    g = _normalize_gender_param(nav_gender)
    if g == 'men':
        return Q(show_in_men=True) | Q(show_in_unisex=True)
    if g == 'women':
        return Q(show_in_women=True) | Q(show_in_unisex=True)
    return Q()


def _category_has_nav_audience_q():
    return Q(show_in_men=True) | Q(show_in_women=True) | Q(show_in_unisex=True)


def _catalog_product_gender_q(gender):
    g = _normalize_gender_param(gender)
    if not g:
        return Q()
    return Q(gender=g) | Q(gender='unisex') | Q(gender__isnull=True)


def _categories_with_listable_products(queryset, restaurant_settings, gender=None):
    """Only categories that have at least one purchasable catalog row for the gender scope."""
    mode = getattr(restaurant_settings, 'catalog_listing_mode', None) or CatalogListingMode.MENU_ITEM
    rs_id = restaurant_settings.pk

    if mode == CatalogListingMode.PRODUCT:
        product_qs = Product.objects.filter(
            category_id=OuterRef('pk'),
            restaurant_settings_id=rs_id,
            is_available=True,
        ).filter(
            Exists(
                MenuItem.objects.filter(
                    product_id=OuterRef('pk'),
                    restaurant_settings_id=rs_id,
                    is_available=True,
                    sku__gte=1,
                )
            )
        )
        gender_q = _catalog_product_gender_q(gender)
        if gender_q:
            product_qs = product_qs.filter(gender_q)
        return queryset.filter(Exists(product_qs))

    menu_qs = MenuItem.objects.filter(
        category_id=OuterRef('pk'),
        restaurant_settings_id=rs_id,
        is_available=True,
        sku__gte=1,
    )
    gender_q = _catalog_product_gender_q(gender)
    if gender_q:
        menu_qs = menu_qs.filter(gender_q)
    return queryset.filter(Exists(menu_qs))


def storefront_categories_queryset(restaurant_settings, gender=None):
    """
    Active, non-placeholder categories for nav/tabs.
    ``gender`` (men/women): nav audience + in-stock catalog for that shopper scope.
    Omitted / all: any category with a nav audience and listable products.
    """
    g = _normalize_gender_param(gender)
    qs = exclude_placeholder_categories(
        Category.objects.filter(
            is_active=True,
            restaurant_settings=restaurant_settings,
        )
    ).filter(_category_has_nav_audience_q())

    if g in ('men', 'women'):
        qs = qs.filter(_category_nav_audience_q(g))

    qs = _categories_with_listable_products(qs, restaurant_settings, gender=g)
    return qs.order_by('sort_order', 'name')
