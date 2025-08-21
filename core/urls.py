from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('restaurant-settings/', views.restaurant_settings, name='restaurant-settings'),
    path('info/', views.public_restaurant_info, name='public_restaurant_info'),
    path('health/', views.health_check, name='health_check'),
    path('status/', views.system_status, name='system_status'),
]
