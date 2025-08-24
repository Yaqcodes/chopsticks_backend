from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('token/refresh/', views.token_refresh_view, name='token_refresh'),
    
    # Password management
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/<str:uidb64>/<str:token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Social authentication
    path('social/login/', views.SocialLoginView.as_view(), name='social_login'),
    path('google/oauth-url/', views.google_oauth_url, name='google_oauth_url'),
    path('google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    
    # User referrals
    path('referrals/', views.user_referrals, name='user_referrals'),
]
