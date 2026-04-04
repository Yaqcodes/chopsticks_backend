"""
Shared catalog queryset for ZMall list + filter-options (server-side filters & sort).
"""

from django.db import connection
from django.db.models import Case, DecimalField, F, Q, When

from .models import Category, MenuItem


def filter_queryset_by_badge(queryset, badge):
    """Filter by badge in a way that works on SQLite and PostgreSQL (and other DBs)."""
    if not badge:
        return queryset
    if connection.vendor == 'sqlite':
        return queryset.filter(badges__icontains=f'"{badge}"')
    return queryset.filter(badges__contains=[badge])


def annotate_effective_price(queryset):
    return queryset.annotate(
        effective_price=Case(
            When(Q(on_sale=True) & Q(sale_price__isnull=False), then=F('sale_price')),
            default=F('price'),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )


def _apply_size_filter(queryset, size_str):
    if not size_str or not str(size_str).strip():
        return queryset
    size = str(size_str).strip()
    if connection.vendor == 'sqlite':
        return queryset.filter(sizes__icontains=f'"{size}"')
    return queryset.filter(sizes__contains=[size])


def _apply_color_filter(queryset, color_name):
    if not color_name or not str(color_name).strip():
        return queryset
    c = str(color_name).strip()
    return queryset.filter(colors__icontains=c)


def _apply_price_band_on_annotated(qs, band):
    if not band or not str(band).strip():
        return qs
    band = str(band).strip()
    if band == '0-50000':
        return qs.filter(effective_price__lt=50000)
    if band == '50000-100000':
        return qs.filter(effective_price__gte=50000, effective_price__lte=100000)
    if band == '100000-200000':
        return qs.filter(effective_price__gte=100000, effective_price__lte=200000)
    if band == '200000-':
        return qs.filter(effective_price__gte=200000)
    return qs


def _apply_sort_on_annotated(qs, sort_param):
    sort = (sort_param or 'newest').strip()
    if sort == 'price-asc':
        return qs.order_by('effective_price', 'id')
    if sort == 'price-desc':
        return qs.order_by('-effective_price', 'id')
    if sort == 'name':
        return qs.order_by('name', 'id')
    return qs.order_by('-created_at', 'id')


def menu_items_base_catalog_queryset(request, restaurant_settings):
    """
    Tenant + category + badge + on_sale + min/max list price + ids + gender.
    Search and DjangoFilter (category, is_featured) are applied by ListAPIView.filter_queryset.
    """
    queryset = MenuItem.objects.filter(
        is_available=True,
        restaurant_settings=restaurant_settings,
    )

    category_id = request.query_params.get('category_id')
    category_slug = request.query_params.get('category_slug')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    elif category_slug:
        category = Category.objects.filter(
            restaurant_settings=restaurant_settings,
            slug=category_slug.strip(),
        ).first()
        if category:
            queryset = queryset.filter(category=category)

    badge = request.query_params.get('badge')
    queryset = filter_queryset_by_badge(queryset, badge)

    on_sale_param = request.query_params.get('on_sale')
    if on_sale_param is not None and str(on_sale_param).strip().lower() in ('1', 'true', 'yes'):
        queryset = queryset.filter(on_sale=True)

    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)

    gender = request.query_params.get('gender')
    if gender and str(gender).strip().lower() not in ('', 'all'):
        g = str(gender).strip().lower()
        queryset = queryset.filter(Q(gender=g) | Q(gender='unisex'))

    ids_param = request.query_params.get('ids')
    if ids_param:
        try:
            id_list = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
            if id_list:
                ordering = Case(*[When(id=x, then=pos) for pos, x in enumerate(id_list)])
                queryset = queryset.filter(id__in=id_list).order_by(ordering)
        except (ValueError, TypeError):
            pass

    return queryset


def apply_menu_item_style_filters_and_sort(queryset, request):
    """
    After SearchFilter: color, size, price_band (effective price), sort.
    When `ids` is set, preserve id-list ordering (e.g. curated grids).
    """
    has_ids = bool(request.query_params.get('ids', '').strip())
    color = request.query_params.get('color')
    size = request.query_params.get('size')
    price_band = request.query_params.get('price_band')
    sort = request.query_params.get('sort') or 'newest'

    qs = annotate_effective_price(queryset)
    if color:
        qs = _apply_color_filter(qs, color)
    if size:
        qs = _apply_size_filter(qs, size)
    if price_band:
        qs = _apply_price_band_on_annotated(qs, price_band)

    if has_ids:
        return qs

    return _apply_sort_on_annotated(qs, sort)
