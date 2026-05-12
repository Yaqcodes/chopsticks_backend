"""
Queryset helpers for grouped Product catalog (Zmall storefront).
"""

from django.db.models import (
    Case,
    DecimalField,
    Exists,
    F,
    Min,
    OuterRef,
    Q,
    When,
)

from .models import MenuItem, Product
from .catalog_queryset import filter_queryset_by_badge
from .size_sort import size_sort_key


def has_purchasable_variant_subquery():
    """At least one linked variant: available and in stock (sku >= 1)."""
    return Exists(
        MenuItem.objects.filter(
            product_id=OuterRef('pk'),
            restaurant_settings_id=OuterRef('restaurant_settings_id'),
            is_available=True,
            sku__gte=1,
        )
    )


def products_base_queryset(request, restaurant_settings, search_text=None):
    """
    Tenant + category + badge + on_sale + gender + ids + search (Product fields + variant barcode).
    Does not apply style filters (color/size/price_band/sort).
    """
    qs = (
        Product.objects.filter(
            restaurant_settings=restaurant_settings,
            is_available=True,
        )
        .filter(has_purchasable_variant_subquery())
        .select_related('category')
    )

    category_id = request.query_params.get('category_id')
    category_slug = request.query_params.get('category_slug')
    if category_id:
        qs = qs.filter(category_id=category_id)
    elif category_slug:
        qs = qs.filter(category__slug=category_slug.strip())

    badge = request.query_params.get('badge')
    qs = filter_queryset_by_badge(qs, badge)

    on_sale_param = request.query_params.get('on_sale')
    if on_sale_param is not None and str(on_sale_param).strip().lower() in ('1', 'true', 'yes'):
        qs = qs.filter(
            Exists(
                MenuItem.objects.filter(
                    product_id=OuterRef('pk'),
                    restaurant_settings_id=OuterRef('restaurant_settings_id'),
                    on_sale=True,
                )
            )
        )

    gender = request.query_params.get('gender')
    if gender and str(gender).strip().lower() not in ('', 'all'):
        g = str(gender).strip().lower()
        qs = qs.filter(Q(gender=g) | Q(gender='unisex') | Q(gender__isnull=True))

    is_featured = request.query_params.get('is_featured')
    if is_featured is not None and str(is_featured).strip().lower() in ('1', 'true', 'yes'):
        qs = qs.filter(is_featured=True)

    ids_param = request.query_params.get('ids')
    if ids_param:
        try:
            id_list = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
            if id_list:
                qs = qs.filter(id__in=id_list)
        except (ValueError, TypeError):
            pass

    if search_text is not None:
        search = (search_text or '').strip()
    else:
        search = (request.query_params.get('search') or '').strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(meta_title__icontains=search)
            | Q(slug__icontains=search)
            | Exists(
                MenuItem.objects.filter(
                    product_id=OuterRef('pk'),
                    restaurant_settings_id=OuterRef('restaurant_settings_id'),
                ).filter(Q(name__icontains=search) | Q(barcode__icontains=search))
            )
        )

    return qs.distinct()


def _apply_product_color_filter(qs, color_name):
    if not color_name or not str(color_name).strip():
        return qs
    c = str(color_name).strip()
    return qs.filter(
        Exists(
            MenuItem.objects.filter(product_id=OuterRef('pk'), colors__icontains=c)
        )
    )


def _apply_product_size_filter(qs, size_str):
    if not size_str or not str(size_str).strip():
        return qs
    size = str(size_str).strip()
    return qs.filter(
        Exists(
            MenuItem.objects.filter(
                product_id=OuterRef('pk'),
            ).filter(size__iexact=size)
        )
    )


def _apply_product_price_band(qs, band):
    """Requires `_min_variant_price` annotation on qs."""
    if not band or not str(band).strip():
        return qs
    band = str(band).strip()
    if band == '0-50000':
        return qs.filter(_min_variant_price__lt=50000)
    if band == '50000-100000':
        return qs.filter(_min_variant_price__gte=50000, _min_variant_price__lte=100000)
    if band == '100000-200000':
        return qs.filter(_min_variant_price__gte=100000, _min_variant_price__lte=200000)
    if band == '200000-':
        return qs.filter(_min_variant_price__gte=200000)
    return qs


def _apply_product_sort(qs, sort_param):
    sort = (sort_param or 'newest').strip()
    if sort == 'price-asc':
        return qs.order_by('_min_variant_price', 'id')
    if sort == 'price-desc':
        return qs.order_by('-_min_variant_price', 'id')
    if sort == 'name':
        return qs.order_by('name', 'id')
    return qs.order_by('-created_at', 'id')


def annotate_products_min_variant_price(qs):
    """Annotate queryset of Product rows with `_min_variant_price`` (effective price across variants)."""
    return qs.annotate(
        _min_variant_price=Min(
            Case(
                When(
                    Q(variants__on_sale=True) & Q(variants__sale_price__isnull=False),
                    then=F('variants__sale_price'),
                ),
                default=F('variants__price'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        ),
    )


def apply_product_style_filters_and_sort(qs, request):
    """After base queryset: color, size, effective price band, sort (uses variant min effective price)."""
    has_ids = bool(request.query_params.get('ids', '').strip())
    color = request.query_params.get('color')
    size = request.query_params.get('size')
    price_band = request.query_params.get('price_band')
    sort = request.query_params.get('sort') or 'newest'

    qs = annotate_products_min_variant_price(qs)
    if color:
        qs = _apply_product_color_filter(qs, color)
    if size:
        qs = _apply_product_size_filter(qs, size)
    if price_band:
        qs = _apply_product_price_band(qs, price_band)

    if has_ids:
        return qs

    return _apply_product_sort(qs, sort)


def product_filter_options_aggregate(request, restaurant_settings):
    """Distinct color names and sizes from variants of products in base scope."""
    base = products_base_queryset(request, restaurant_settings)
    ids = list(base.values_list('id', flat=True))
    qs = MenuItem.objects.filter(product_id__in=ids, restaurant_settings=restaurant_settings)
    names = set()
    sizes_out = set()
    for colors, size in qs.values_list('colors', 'size').iterator(chunk_size=500):
        if colors and isinstance(colors, list):
            for c in colors:
                if isinstance(c, dict):
                    name = (c.get('name') or '').strip()
                    if name:
                        names.add(name)
        if size and str(size).strip():
            sizes_out.add(str(size).strip())
    return {
        'colors': sorted(names, key=str.lower),
        'sizes': sorted(sizes_out, key=size_sort_key),
    }


def variant_is_purchasable(menuitem):
    return bool(menuitem.is_available and menuitem.sku >= 1)
