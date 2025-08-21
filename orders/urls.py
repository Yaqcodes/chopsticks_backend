from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Order CRUD operations
    path('', views.OrderListView.as_view(), name='order_list'),
    path('admin/', views.AdminOrderListView.as_view(), name='admin_order_list'),
    path('create/', views.create_order, name='create_order'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Order tracking
    path('tracking/<str:order_number>/', views.order_tracking, name='order_tracking'),
    
    # Cart and delivery calculations
    path('calculate-totals/', views.calculate_cart_totals_view, name='calculate_cart_totals'),
    path('calculate-delivery-fee/', views.calculate_delivery_fee_view, name='calculate_delivery_fee'),
    
    # Admin operations
    path('<int:order_id>/status/', views.update_order_status, name='update_order_status'),
]
