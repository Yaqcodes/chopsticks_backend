from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.redirect_to_guide, name='root_redirect'),
    path('restaurant-settings/', views.restaurant_settings, name='restaurant-settings'),
    path('info/', views.public_restaurant_info, name='public_restaurant_info'),
    path('health/', views.health_check, name='health_check'),
    path('status/', views.system_status, name='system_status'),
    path('user-guide/', views.user_guide, name='user_guide'),
]
