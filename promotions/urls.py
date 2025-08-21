from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    # Promo code management
    path('', views.PromoCodeListView.as_view(), name='promo_code_list'),
    path('active/', views.ActivePromotionsView.as_view(), name='active_promotions'),
    path('validate/', views.validate_promo_code, name='validate_promo_code'),
    path('usage/', views.user_promo_usage, name='user_promo_usage'),
    path('<str:code>/', views.promo_code_details, name='promo_code_details'),
    path('apply/<int:order_id>/', views.apply_promo_to_order, name='apply_promo_to_order'),
]
