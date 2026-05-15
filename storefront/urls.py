from django.urls import path

from . import views

app_name = 'storefront'

urlpatterns = [
    path('spotlights/', views.spotlight_list, name='spotlight_list'),
]
