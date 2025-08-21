from django.urls import path
from . import views

app_name = 'loyalty'

urlpatterns = [
    # Points management
    path('points/', views.UserPointsView.as_view(), name='user_points'),
    path('points/history/', views.PointsHistoryView.as_view(), name='points_history'),
    path('points/calculate-earning/', views.calculate_points_earning, name='calculate_points_earning'),
    
    # Rewards
    path('rewards/available/', views.AvailableRewardsView.as_view(), name='available_rewards'),
    path('rewards/my-rewards/', views.UserRewardsView.as_view(), name='user_rewards'),
    path('rewards/redeem/', views.redeem_reward, name='redeem_reward'),
    path('rewards/<int:reward_id>/use/', views.use_reward, name='use_reward'),
    
    # Referral system
    path('referral/process/', views.process_referral_bonus_view, name='process_referral_bonus'),
    
    # Summary
    path('summary/', views.loyalty_summary, name='loyalty_summary'),
    
    # QR Code Loyalty Card
    path('scan-card/', views.scan_loyalty_card_view, name='scan_loyalty_card'),
    path('loyalty-card/', views.get_loyalty_card, name='get_loyalty_card'),
    path('regenerate-qr/', views.regenerate_qr_code, name='regenerate_qr_code'),
]
