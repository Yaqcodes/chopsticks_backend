from django.urls import path
from . import views

app_name = 'addresses'

urlpatterns = [
    # Address CRUD operations
    path('', views.AddressListView.as_view(), name='address_list'),
    path('<int:pk>/', views.AddressDetailView.as_view(), name='address_detail'),
    path('<int:address_id>/set-default/', views.set_default_address, name='set_default_address'),
    
    # Geocoding
    path('geocode/', views.geocode_address_view, name='geocode_address'),
    
    # Default address
    path('default/', views.default_address, name='default_address'),
]
