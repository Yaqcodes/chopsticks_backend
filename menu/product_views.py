"""Grouped catalog Product APIs (additive; POS still uses MenuItem APIs)."""

from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from core.utils import get_business_from_request

from .audit import log_product_variant_link
from .product_list_facets import bulk_attach_variant_facets_for_products
from .models import MenuItem, Product, ProductImage
from .pagination import MenuItemPageNumberPagination
from .product_catalog import (
    annotate_products_min_variant_price,
    apply_product_style_filters_and_sort,
    has_purchasable_variant_subquery,
    product_filter_options_aggregate,
    products_base_queryset,
)
from .product_link_service import link_menu_items_to_product, unlink_menu_item_from_product
from .serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
)


def prefetch_product_list_gallery(queryset):
    """Prefetch gallery images only; variant facets are bulk-loaded in ``list()`` (one query per page)."""
    return queryset.prefetch_related(
        Prefetch(
            'gallery_images',
            queryset=ProductImage.objects.order_by('sort_order', 'id'),
        ),
    )


class CatalogProductListFacetsMixin:
    """Attach ``_list_facet_*`` on each page row before serialization (single MenuItem query per page)."""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            bulk_attach_variant_facets_for_products(page)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        products = list(queryset)
        bulk_attach_variant_facets_for_products(products)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class ProductListView(CatalogProductListFacetsMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = MenuItemPageNumberPagination

    def get_queryset(self):
        rs = get_business_from_request(self.request)
        qs = products_base_queryset(self.request, rs)
        qs = qs.annotate(variant_count=Count('variants', distinct=True))
        qs = prefetch_product_list_gallery(qs)
        return apply_product_style_filters_and_sort(qs, self.request)


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer

    def get_queryset(self):
        rs = get_business_from_request(self.request)
        variant_qs = MenuItem.objects.select_related('category').prefetch_related('extra_images')
        qs = annotate_products_min_variant_price(
            Product.objects.filter(restaurant_settings=rs, is_available=True),
        )
        return qs.select_related('category').prefetch_related(
            Prefetch(
                'gallery_images',
                queryset=ProductImage.objects.order_by('sort_order', 'id'),
            ),
            Prefetch('variants', queryset=variant_qs),
        )


class FeaturedProductsView(CatalogProductListFacetsMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = MenuItemPageNumberPagination

    def get_queryset(self):
        rs = get_business_from_request(self.request)
        qs = Product.objects.filter(
            restaurant_settings=rs,
            is_featured=True,
            is_available=True,
        ).filter(has_purchasable_variant_subquery())
        qs = qs.annotate(variant_count=Count('variants', distinct=True))
        qs = annotate_products_min_variant_price(qs)
        qs = qs.select_related('category')
        qs = prefetch_product_list_gallery(qs)
        return qs.order_by('sort_order', '-created_at', 'name')


class ProductManageMixin:
    permission_classes = [IsAdminUser]
    serializer_class = ProductWriteSerializer

    def get_queryset(self):
        rs = get_business_from_request(self.request)
        return Product.objects.filter(restaurant_settings=rs)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['restaurant_settings'] = get_business_from_request(self.request)
        return ctx


class ProductCreateView(ProductManageMixin, generics.CreateAPIView):
    pass


class ProductUpdateView(ProductManageMixin, generics.UpdateAPIView):
    pass


class ProductDeleteView(ProductManageMixin, generics.DestroyAPIView):
    pass


@api_view(['GET'])
@permission_classes([AllowAny])
def catalog_product_filter_options(request):
    rs = get_business_from_request(request)
    payload = product_filter_options_aggregate(request, rs)
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def catalog_product_search(request):
    restaurant_settings = get_business_from_request(request)
    query = request.query_params.get('q', '')
    if not str(query).strip():
        return Response({'error': 'Search query is required.'}, status=status.HTTP_400_BAD_REQUEST)

    queryset = (
        products_base_queryset(request, restaurant_settings, search_text=query.strip())
        .distinct()
        .annotate(variant_count=Count('variants', distinct=True))
    )
    queryset = prefetch_product_list_gallery(queryset)
    queryset = apply_product_style_filters_and_sort(queryset, request)

    products = list(queryset)
    bulk_attach_variant_facets_for_products(products)
    serializer = ProductListSerializer(products, many=True)
    data = serializer.data
    return Response({
        'query': query.strip(),
        'results': data,
        'count': len(data),
    })


def _tenant_menu_items_for_link(rs):
    """MenuItems scoped to business (avoid cross-tenant link)."""
    return MenuItem.objects.filter(restaurant_settings=rs)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def product_link_variants(request, pk):
    rs = get_business_from_request(request)
    product = get_object_or_404(Product.objects.filter(restaurant_settings=rs), pk=pk)

    raw_ids = request.data.get('menuitem_ids')
    raw_barcodes = request.data.get('barcodes')
    items = []
    if raw_ids and isinstance(raw_ids, list):
        items.extend(list(_tenant_menu_items_for_link(rs).filter(pk__in=raw_ids)))
    if raw_barcodes and isinstance(raw_barcodes, list):
        codes = [str(b).strip() for b in raw_barcodes if str(b).strip()]
        items.extend(list(_tenant_menu_items_for_link(rs).filter(barcode__in=codes)))

    seen = set()
    uniq = []
    for m in items:
        if m.pk not in seen:
            seen.add(m.pk)
            uniq.append(m)

    dry_run = str(request.query_params.get('dry_run', '')).lower() in ('1', 'true', 'yes')

    result = link_menu_items_to_product(product, uniq, dry_run=dry_run)
    if dry_run:
        return Response(result, status=status.HTTP_200_OK)
    if result.get('errors'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    for mid, prev in result.get('linked_events', []):
        log_product_variant_link(
            request,
            action='link',
            product_id=product.pk,
            menu_item_id=mid,
            previous_product_id=prev,
        )
    return Response(result, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def product_unlink_variant(request, pk, menuitem_id):
    rs = get_business_from_request(request)
    product = get_object_or_404(Product.objects.filter(restaurant_settings=rs), pk=pk)
    menu_item = get_object_or_404(_tenant_menu_items_for_link(rs), pk=menuitem_id)
    prev_pid = menu_item.product_id

    ok, err_msg = unlink_menu_item_from_product(product, menu_item)
    if not ok:
        return Response({'error': err_msg}, status=status.HTTP_400_BAD_REQUEST)

    log_product_variant_link(
        request,
        action='unlink',
        product_id=product.pk,
        menu_item_id=menu_item.pk,
        previous_product_id=prev_pid,
    )

    return Response({'ok': True, 'menu_item_id': menu_item.pk}, status=status.HTTP_200_OK)
