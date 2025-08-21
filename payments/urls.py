from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initialize/', views.initialize_payment, name='initialize_payment'),
    path('verify/<str:reference>/', views.verify_payment, name='verify_payment'),
    path('webhook/', views.PaystackWebhookView.as_view(), name='webhook'),
    path('callback/', views.payment_callback, name='payment_callback'),  # Add missing callback endpoint
]
