from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # Category endpoints
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:category_id>/items/', views.menu_by_category, name='menu_by_category'),
    
    # Menu item endpoints (filter-options before <int:pk> so it is not captured as an id)
    path('items/filter-options/', views.menu_item_filter_options, name='menu_item_filter_options'),
    path('items/', views.MenuItemListView.as_view(), name='menu_item_list'),
    path('items/<int:pk>/', views.MenuItemDetailView.as_view(), name='menu_item_detail'),
    
    # Featured items
    path('featured/', views.FeaturedItemsView.as_view(), name='featured_items'),
    
    # Search
    path('search/', views.menu_search, name='menu_search'),
    path('barcode/<str:barcode>/', views.menu_item_by_barcode, name='menu-by-barcode'),

    # Category mutations
    path('categories/create/', views.CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category-delete'),

    # MenuItem mutations
    path('items/create/', views.MenuItemCreateView.as_view(), name='menuitem-create'),
    path('items/id/<int:pk>/update/', views.MenuItemUpdateView.as_view(), name='menuitem-update'),
    path('items/bc/<str:barcode>/update/', views.MenuItemUpdateView.as_view(), name='menuitem-update'),
    path('items/id/<int:pk>/delete/', views.MenuItemDeleteView.as_view(), name='menuitem-delete'),
    path('items/bc/<str:barcode>/delete/', views.MenuItemDeleteView.as_view(), name='menuitem-delete'),
]
