from django.contrib.admin import AdminSite
from django.utils.html import format_html
from .admin import (
    UserPointsAdmin, PointsTransactionAdmin, RewardAdmin, 
    UserRewardAdmin, LoyaltyCardAdmin
)
from .models import UserPoints, PointsTransaction, Reward, UserReward, LoyaltyCard


class RestaurantAdminSite(AdminSite):
    """Custom admin site for restaurant management."""
    
    site_header = format_html(
        '<div style="background: linear-gradient(135deg, #dc3545 0%, #8b0000 100%); '
        'color: white; padding: 20px; margin: -20px -20px 20px -20px; '
        'border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">'
        '<h1 style="margin: 0; font-size: 24px; font-weight: bold;">🍜 Chopsticks & Bowls</h1>'
        '<p style="margin: 5px 0 0 0; opacity: 0.9;">Restaurant Management System</p>'
        '</div>'
    )
    site_title = "Chopsticks & Bowls Admin"
    index_title = "Restaurant Dashboard"
    
    def each_context(self, request):
        """Add custom context for all admin pages."""
        context = super().each_context(request)
        context['custom_css'] = self.get_custom_css()
        return context
    
    def get_custom_css(self):
        """Return custom CSS for restaurant theme."""
        return """
        <style>
        /* Restaurant Theme CSS */
        :root {
            --primary-color: #dc3545;
            --primary-dark: #8b0000;
            --secondary-color: #343a40;
            --accent-color: #ffc107;
            --success-color: #28a745;
            --danger-color: #dc3545;
            --warning-color: #ffc107;
            --info-color: #17a2b8;
            --light-color: #f8f9fa;
            --dark-color: #343a40;
        }
        
        /* Header and Navigation */
        #header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        #branding h1 {
            color: white !important;
            font-weight: bold;
        }
        
        .module h2, .module caption, .inline-group h2 {
            background: var(--primary-color);
            color: white;
            border-radius: 5px 5px 0 0;
        }
        
        /* Buttons */
        .button, input[type=submit], input[type=button], .submit-row input, a.button {
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        
        .button:hover, input[type=submit]:hover, input[type=button]:hover, 
        .submit-row input:hover, a.button:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .button.default, input[type=submit].default, .submit-row input.default {
            background: var(--success-color);
        }
        
        .button.default:hover, input[type=submit].default:hover, 
        .submit-row input.default:hover {
            background: #1e7e34;
        }
        
        /* Tables */
        #result_list {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        #result_list thead th {
            background: var(--secondary-color);
            color: white;
            border: none;
            padding: 12px 8px;
        }
        
        #result_list tbody tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        #result_list tbody tr:hover {
            background-color: #e9ecef;
        }
        
        /* Form Fields */
        .form-row {
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 4px solid var(--primary-color);
        }
        
        .form-row label {
            font-weight: bold;
            color: var(--secondary-color);
        }
        
        .form-row input, .form-row select, .form-row textarea {
            border: 2px solid #e9ecef;
            border-radius: 5px;
            padding: 8px 12px;
            transition: border-color 0.3s ease;
        }
        
        .form-row input:focus, .form-row select:focus, .form-row textarea:focus {
            border-color: var(--primary-color);
            outline: none;
            box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
        }
        
        /* Status Indicators */
        .status-active {
            color: var(--success-color);
            font-weight: bold;
        }
        
        .status-inactive {
            color: var(--danger-color);
            font-weight: bold;
        }
        
        .points-high {
            color: var(--success-color);
            font-weight: bold;
        }
        
        .points-medium {
            color: var(--warning-color);
            font-weight: bold;
        }
        
        .points-low {
            color: var(--danger-color);
            font-weight: bold;
        }
        
        /* Dashboard Cards */
        .dashboard-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid var(--primary-color);
        }
        
        .dashboard-card h3 {
            color: var(--secondary-color);
            margin-top: 0;
            font-size: 18px;
        }
        
        .dashboard-stat {
            font-size: 24px;
            font-weight: bold;
            color: var(--primary-color);
        }
        
        /* QR Code Display */
        .qr-code-display {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 10px 0;
        }
        
        .qr-code-text {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            color: var(--secondary-color);
            background: white;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }
        
        /* Action Buttons */
        .action-button {
            display: inline-block;
            padding: 8px 16px;
            margin: 2px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .action-button.primary {
            background: var(--primary-color);
            color: white;
        }
        
        .action-button.success {
            background: var(--success-color);
            color: white;
        }
        
        .action-button.warning {
            background: var(--warning-color);
            color: var(--dark-color);
        }
        
        .action-button.danger {
            background: var(--danger-color);
            color: white;
        }
        
        .action-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .dashboard-card {
                padding: 15px;
            }
            
            .dashboard-stat {
                font-size: 20px;
            }
            
            #result_list {
                font-size: 14px;
            }
        }
        
        /* Loading Animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        </style>
        """


# Create custom admin site instance
restaurant_admin_site = RestaurantAdminSite(name='restaurant_admin')

# Register models with custom admin site
restaurant_admin_site.register(UserPoints, UserPointsAdmin)
restaurant_admin_site.register(PointsTransaction, PointsTransactionAdmin)
restaurant_admin_site.register(Reward, RewardAdmin)
restaurant_admin_site.register(UserReward, UserRewardAdmin)
restaurant_admin_site.register(LoyaltyCard, LoyaltyCardAdmin)

# Add custom URLs for loyalty card management
from django.urls import path
from . import views

# Store the original get_urls method
original_get_urls = restaurant_admin_site.get_urls

def custom_get_urls():
    """Get custom admin URLs."""
    custom_urls = [
        path('loyalty-card/<int:card_id>/link-user/', views.link_loyalty_card_user, name='link_loyalty_card_user'),
        path('loyalty-card/<int:card_id>/link-user/confirm/', views.confirm_link_loyalty_card_user, name='confirm_link_loyalty_card_user'),
    ]
    return custom_urls + original_get_urls()

# Replace the get_urls method
restaurant_admin_site.get_urls = custom_get_urls
