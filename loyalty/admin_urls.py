from django.urls import path
from . import views

app_name = 'loyalty'

urlpatterns = [
    # QR Code Scanning Admin Routes
    path('qr-scan-dashboard/', views.qr_scan_dashboard, name='qr_scan_dashboard'),
    path('qr-scan-interface/', views.qr_scan_interface, name='qr_scan_interface'),
    path('qr-scan-api/', views.QRScanAPIView.as_view(), name='qr_scan_api'),
    path('loyalty-card/<int:card_id>/', views.loyalty_card_detail, name='loyalty_card_detail'),
    
    # Loyalty Card Management Routes
    path('loyalty-card/<int:card_id>/link-user/', views.link_loyalty_card_user, name='link_loyalty_card_user'),
    path('loyalty-card/<int:card_id>/link-user/confirm/', views.confirm_link_loyalty_card_user, name='confirm_link_loyalty_card_user'),
]
