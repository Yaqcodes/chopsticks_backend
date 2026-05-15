"""Resolve spotlight posts and linked catalog rows for public APIs."""

from decimal import Decimal

from django.db.models import Prefetch

from core.models import CatalogListingMode
from menu.models import MenuItem, MenuItemImage, Product, ProductImage
from menu.product_catalog import (
    annotate_products_min_variant_price,
    has_purchasable_variant_subquery,
)
from menu.product_list_facets import bulk_attach_variant_facets_for_products
from menu.serializers import MenuItemSerializer, ProductListSerializer, _media_url

from .models import SpotlightPost, SpotlightPostLink


def _decimal_price(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal('0.01')))
    return str(value)


def _url_from_image_field(filefield):
    if not filefield:
        return None
    name = getattr(filefield, 'name', None)
    if name:
        return _media_url(name)
    raw = str(filefield).strip()
    return _media_url(raw) if raw else None


def _url_from_legacy_images_list(images):
    """MenuItem.images JSON may hold paths or URLs."""
    if not images or not isinstance(images, list):
        return None
    for entry in images:
        if not entry or not isinstance(entry, str):
            continue
        s = entry.strip()
        if not s:
            continue
        if s.startswith('http://') or s.startswith('https://'):
            return s
        return _media_url(s.lstrip('/'))
    return None


def _menu_item_image_url(menu_item):
    """Primary image, then extra_images, then legacy JSON — same order as MenuItemDetailSerializer."""
    url = _url_from_image_field(menu_item.image)
    if url:
        return url
    extra_qs = getattr(menu_item, 'extra_images', None)
    if extra_qs is not None:
        for extra in extra_qs.all().order_by('sort_order', 'id'):
            url = _url_from_image_field(extra.image)
            if url:
                return url
    return _url_from_legacy_images_list(menu_item.images)


def _product_variant_queryset():
    return (
        MenuItem.objects.filter(is_available=True, sku__gte=1)
        .prefetch_related(
            Prefetch(
                'extra_images',
                queryset=MenuItemImage.objects.order_by('sort_order', 'id'),
            ),
        )
        .order_by('size', 'id')
    )


def resolve_product_image_url(product):
    """
    Grouped Product (Zmall): gallery, then linked variant SKUs (with extras / legacy).
    """
    gallery = getattr(product, 'gallery_images', None)
    if gallery is not None:
        for gi in gallery.all().order_by('sort_order', 'id'):
            url = _url_from_image_field(gi.image)
            if url:
                return url
    else:
        for gi in ProductImage.objects.filter(product_id=product.pk).order_by('sort_order', 'id'):
            url = _url_from_image_field(gi.image)
            if url:
                return url

    variants = getattr(product, 'variants', None)
    if variants is not None:
        variant_rows = variants.all()
    else:
        variant_rows = _product_variant_queryset().filter(product_id=product.pk)

    for variant in variant_rows:
        url = _menu_item_image_url(variant)
        if url:
            return url
    return None


def resolve_menu_item_image_url(menu_item):
    """Menu-item tenants: single SKU row image resolution."""
    return _menu_item_image_url(menu_item)


def _item_from_product(product):
    data = ProductListSerializer(product).data
    price = data.get('min_variant_price')
    if price is None:
        price = data.get('base_price')
    return {
        'ref_type': 'product',
        'ref_id': product.id,
        'name': data.get('name') or product.name,
        'image_url': resolve_product_image_url(product),
        'price': _decimal_price(price),
        'detail_path': f'/product/{product.id}',
    }


def _item_from_menu_item(menu_item):
    data = MenuItemSerializer(menu_item).data
    price = data.get('effective_price')
    if price is None:
        price = data.get('price')
    return {
        'ref_type': 'menu_item',
        'ref_id': menu_item.id,
        'name': data.get('name') or menu_item.name,
        'image_url': resolve_menu_item_image_url(menu_item),
        'price': _decimal_price(price),
        'detail_path': f'/item/{menu_item.id}',
    }


def _prefetch_spotlight_posts(restaurant_settings, placement):
    return (
        SpotlightPost.objects.filter(
            restaurant_settings=restaurant_settings,
            placement=placement,
            is_active=True,
        )
        .prefetch_related(
            Prefetch(
                'links',
                queryset=SpotlightPostLink.objects.select_related(
                    'product',
                    'menu_item',
                    'product__category',
                    'menu_item__category',
                ).order_by('sort_order', 'id'),
            ),
        )
        .order_by('sort_order', '-created_at', 'id')
    )


def _load_products_for_links(product_ids, restaurant_settings):
    if not product_ids:
        return {}
    qs = (
        Product.objects.filter(
            id__in=product_ids,
            restaurant_settings=restaurant_settings,
            is_available=True,
        )
        .filter(has_purchasable_variant_subquery())
        .select_related('category')
    )
    qs = annotate_products_min_variant_price(qs)
    qs = qs.prefetch_related(
        Prefetch(
            'gallery_images',
            queryset=ProductImage.objects.order_by('sort_order', 'id'),
        ),
        Prefetch(
            'variants',
            queryset=_product_variant_queryset(),
        ),
    )
    products = list(qs)
    bulk_attach_variant_facets_for_products(products)
    return {p.id: p for p in products}


def _load_menu_items_for_links(menu_item_ids, restaurant_settings):
    if not menu_item_ids:
        return {}
    qs = (
        MenuItem.objects.filter(
            id__in=menu_item_ids,
            restaurant_settings=restaurant_settings,
            is_available=True,
            sku__gte=1,
        )
        .select_related('category')
        .prefetch_related(
            Prefetch(
                'extra_images',
                queryset=MenuItemImage.objects.order_by('sort_order', 'id'),
            ),
        )
    )
    return {m.id: m for m in qs}


def build_spotlights_payload(restaurant_settings, placement):
    """Return API-ready dict for GET /api/storefront/spotlights/."""
    mode = restaurant_settings.catalog_listing_mode
    posts = list(_prefetch_spotlight_posts(restaurant_settings, placement))

    product_ids = []
    menu_item_ids = []
    for post in posts:
        for link in post.links.all():
            if link.product_id:
                product_ids.append(link.product_id)
            if link.menu_item_id:
                menu_item_ids.append(link.menu_item_id)

    product_map = (
        _load_products_for_links(product_ids, restaurant_settings)
        if mode == CatalogListingMode.PRODUCT
        else {}
    )
    menu_item_map = (
        _load_menu_items_for_links(menu_item_ids, restaurant_settings)
        if mode == CatalogListingMode.MENU_ITEM
        else {}
    )

    spotlight_rows = []
    for post in posts:
        items = []
        for link in post.links.all():
            if mode == CatalogListingMode.PRODUCT and link.product_id:
                product = product_map.get(link.product_id)
                if product:
                    items.append(_item_from_product(product))
            elif mode == CatalogListingMode.MENU_ITEM and link.menu_item_id:
                menu_item = menu_item_map.get(link.menu_item_id)
                if menu_item:
                    items.append(_item_from_menu_item(menu_item))

        image_url = _media_url(post.image.name) if post.image else None
        spotlight_rows.append({
            'id': post.id,
            'image_url': image_url,
            'external_url': post.external_url or '',
            'caption': post.caption,
            'cta_label': post.cta_label or 'Shop the look',
            'sort_order': post.sort_order,
            'items': items,
        })

    return {
        'catalog_listing_mode': mode,
        'placement': placement,
        'spotlights': spotlight_rows,
    }
