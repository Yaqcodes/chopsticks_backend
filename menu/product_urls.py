"""Public + admin routes for grouped catalog Product (under /api/products/)."""

from django.urls import path

from . import product_views

urlpatterns = [
    path('products/', product_views.ProductListView.as_view(), name='product-list'),
    path('products/filter-options/', product_views.catalog_product_filter_options, name='product-filter-options'),
    path('products/search/', product_views.catalog_product_search, name='product-search'),
    path('products/featured/', product_views.FeaturedProductsView.as_view(), name='product-featured'),
    path('products/create/', product_views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', product_views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', product_views.ProductDeleteView.as_view(), name='product-delete'),
    path('products/<int:pk>/link-variants/', product_views.product_link_variants, name='product-link-variants'),
    path(
        'products/<int:pk>/unlink-variant/<int:menuitem_id>/',
        product_views.product_unlink_variant,
        name='product-unlink-variant',
    ),
    path('products/<int:pk>/', product_views.ProductDetailView.as_view(), name='product-detail'),
]
