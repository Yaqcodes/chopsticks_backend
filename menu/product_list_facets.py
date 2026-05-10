"""
Bulk variant facet + slim variant rows for catalog Product list APIs.

One ``values()`` iterator per page: facet lists and card-ready variant dicts per product.
Variant size is taken only from ``MenuItem.size`` (not the ``sizes`` JSON field).
"""

from collections import defaultdict
from decimal import Decimal

from django.conf import settings

from .models import MenuItem


def _media_url(path):
    if not path or not str(path).strip():
        return None
    path = str(path).lstrip('/')
    base = (settings.MEDIA_URL or '/media/').rstrip('/')
    return f'{base}/{path}' if path else None


def _colors_from_json(colors):
    if not colors or not isinstance(colors, list):
        return []
    out = []
    for c in colors:
        if not isinstance(c, dict):
            continue
        hex_val = (c.get('hex') or '#000000').strip()
        if not hex_val.startswith('#'):
            hex_val = '#' + hex_val
        name = (c.get('name') or '').strip() or hex_val
        out.append({'name': name, 'hex': hex_val})
    return out


def _sizes_from_row(size):
    """ZMall SKU size comes only from ``MenuItem.size`` (one value per variant row)."""
    if size is not None and str(size).strip():
        return [str(size).strip()]
    return []


def _primary_size_str(row):
    if row.get('size') and str(row['size']).strip():
        return str(row['size']).strip()
    return ''


def _variant_purchasable(row):
    sku = row.get('sku')
    try:
        sku_n = int(sku) if sku is not None else 0
    except (TypeError, ValueError):
        sku_n = 0
    return bool(row.get('is_available') and sku_n >= 1)


def _decimal_to_api_number(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _variant_card_dict(row):
    """JSON-serializable row for storefront matrix (aligned with ProductVariantSerializer shape)."""
    norm = _colors_from_json(row.get('colors') or [])
    color = norm[0] if norm else None
    price = _decimal_to_api_number(row.get('price')) or 0.0
    on_sale = bool(row.get('on_sale'))
    sale_price = _decimal_to_api_number(row.get('sale_price'))
    if on_sale and sale_price is not None:
        eff = sale_price
    else:
        eff = price
    img_name = row.get('image')
    primary = _media_url(img_name) if img_name else None
    images = [primary] if primary else []
    return {
        'id': row['id'],
        'size': _primary_size_str(row),
        'color': color,
        'price': price,
        'on_sale': on_sale,
        'sale_price': sale_price,
        'effective_price': eff,
        'sku': row.get('sku') or 0,
        'is_available': _variant_purchasable(row),
        'image': primary,
        'images': images,
    }


def bulk_attach_variant_facets_for_products(products):
    """
    Mutates each Product in ``products`` with:
      - ``_list_facet_sizes``, ``_list_facet_colors`` (facet lists)
      - ``_list_variant_cards`` (slim variant rows for matrix + add-to-cart)
    """
    if not products:
        return
    ids = [p.pk for p in products]
    sizes_by = defaultdict(dict)
    colors_by = defaultdict(dict)
    variants_by = defaultdict(list)

    row_iter = (
        MenuItem.objects.filter(product_id__in=ids)
        .values(
            'id',
            'product_id',
            'size',
            'colors',
            'price',
            'on_sale',
            'sale_price',
            'sku',
            'is_available',
            'image',
        )
        .iterator(chunk_size=500)
    )

    for row in row_iter:
        pid = row['product_id']
        for s in _sizes_from_row(row.get('size')):
            sizes_by[pid][s.lower()] = s
        for c in _colors_from_json(row.get('colors') or []):
            key = str(c.get('name', '')).strip().lower()
            if key and key not in colors_by[pid]:
                colors_by[pid][key] = c
        variants_by[pid].append(_variant_card_dict(row))

    for p in products:
        pid = p.pk
        p._list_facet_sizes = sorted(sizes_by[pid].values(), key=lambda x: str(x).lower())
        p._list_facet_colors = sorted(colors_by[pid].values(), key=lambda x: str(x.get('name', '')).lower())
        p._list_variant_cards = sorted(
            variants_by[pid],
            key=lambda x: (str(x.get('size') or '').lower(), x['id']),
        )
