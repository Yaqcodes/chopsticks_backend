"""Resolve spotlight posts and linked catalog rows for public APIs."""

from decimal import Decimal

from django.db.models import Prefetch

from core.models import CatalogListingMode
from menu.models import MenuItem, Product, ProductImage
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


def _item_from_product(product):
    data = ProductListSerializer(product).data
    price = data.get('min_variant_price')
    if price is None:
        price = data.get('base_price')
    return {
        'ref_type': 'product',
        'ref_id': product.id,
        'name': data.get('name') or product.name,
        'image_url': data.get('image'),
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
        'image_url': data.get('image'),
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
    )
    products = list(qs)
    bulk_attach_variant_facets_for_products(products)
    return {p.id: p for p in products}


def _load_menu_items_for_links(menu_item_ids, restaurant_settings):
    if not menu_item_ids:
        return {}
    qs = MenuItem.objects.filter(
        id__in=menu_item_ids,
        restaurant_settings=restaurant_settings,
        is_available=True,
        sku__gte=1,
    ).select_related('category')
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
