from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # Category endpoints
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:category_id>/items/', views.menu_by_category, name='menu_by_category'),
    
    # Menu item endpoints
    path('items/', views.MenuItemListView.as_view(), name='menu_item_list'),
    path('items/<int:pk>/', views.MenuItemDetailView.as_view(), name='menu_item_detail'),
    
    # Featured items
    path('featured/', views.FeaturedItemsView.as_view(), name='featured_items'),
    
    # Search
    path('search/', views.menu_search, name='menu_search'),
]
