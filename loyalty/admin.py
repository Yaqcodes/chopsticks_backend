from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django import forms
from .models import LoyaltyCard, UserPoints, PointsTransaction, Reward, UserReward
from core.admin_sites import chopsticks_admin_site


class BusinessAdminMixin:
    """
    Mixin to add permission methods for business admin classes.
    
    Ensures that staff users linked to the business can view and manage models.
    """
    
    def has_module_permission(self, request):
        """Check if user can view this app in admin."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """Check if user can view this model."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Check if user can add objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """Check if user can change objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Check if user can delete objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff


class LoyaltyCardForm(forms.ModelForm):
    """Custom form for LoyaltyCard with enhanced QR code field."""
    
    class Meta:
        model = LoyaltyCard
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['qr_code'].help_text = (
            'Enter a customer ID (1-1000) or a LOYALTY- format code. '
            'Customer IDs will generate Google Apps Script URLs automatically.'
        )
        self.fields['qr_code'].widget.attrs.update({
            'placeholder': 'e.g., 1000 or LOYALTY-A1B2C3D4E5F6',
            'style': 'font-family: monospace; font-size: 14px;'
        })


class LoyaltyCardAdmin(BusinessAdminMixin, admin.ModelAdmin):
    form = LoyaltyCardForm
    list_display = ['qr_code', 'user_display', 'status_display', 'created_at', 'last_scan', 'google_url_display']
    list_filter = ['is_active', 'created_at', 'last_scan']
    search_fields = ['qr_code', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'last_scan', 'google_script_url']
    actions = ['link_to_user', 'activate_cards', 'deactivate_cards', 'unlink_users']
    
    def changelist_view(self, request, extra_context=None):
        """Add QR scan quick actions to the changelist view (CB admin only)."""
        extra_context = extra_context or {}
        
        # Only show QR actions in Chopsticks admin (not in main admin or Roschi admin)
        if hasattr(self.admin_site, 'business_identifier') and self.admin_site.business_identifier == 'chopsticks':
            # Add QR scan quick action buttons
            qr_actions = format_html('''
                <div class="module" style="margin-bottom: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding: 15px 20px 10px 20px; margin: 0; font-size: 18px;">
                        🍜 QR Code Scanner Quick Actions
                    </h2>
                    <div style="padding: 20px;">
                        <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px;">
                            <a href="{}" class="button" style="
                                background: #dc3545; 
                                color: white; 
                                padding: 12px 24px; 
                                text-decoration: none; 
                                border-radius: 6px; 
                                font-weight: bold;
                                display: inline-block;
                                transition: all 0.3s ease;
                                border: none;
                                cursor: pointer;
                                font-size: 14px;
                            " onmouseover="this.style.background='#8b0000'; this.style.transform='translateY(-2px)'" 
                               onmouseout="this.style.background='#dc3545'; this.style.transform='translateY(0)'">
                                📱 QR Scan Interface
                            </a>
                            <a href="{}" class="button" style="
                                background: #343a40; 
                                color: white; 
                                padding: 12px 24px; 
                                text-decoration: none; 
                                border-radius: 6px; 
                                font-weight: bold;
                                display: inline-block;
                                transition: all 0.3s ease;
                                border: none;
                                cursor: pointer;
                                font-size: 14px;
                            " onmouseover="this.style.background='#495057'; this.style.transform='translateY(-2px)'" 
                               onmouseout="this.style.background='#343a40'; this.style.transform='translateY(0)'">
                                📊 QR Scan Dashboard
                            </a>
                        </div>
                        <p style="margin: 0; color: #6c757d; font-size: 13px; line-height: 1.4;">
                            <strong>Quick Access:</strong> Use these buttons to quickly navigate to the QR code scanning tools for loyalty card management. 
                            The QR Scan Interface allows staff to scan customer loyalty cards, while the Dashboard provides an overview of recent scans and statistics.
                        </p>
                    </div>
                </div>
            ''', 
            reverse('loyalty:qr_scan_interface'), 
            reverse('loyalty:qr_scan_dashboard')
            )
            
            extra_context['qr_actions'] = qr_actions
        
        return super().changelist_view(request, extra_context)
    
    fieldsets = (
        ('Card Information', {
            'fields': ('qr_code', 'is_active'),
            'description': 'QR code can be manually edited. Use numbers 1-1000 for customer IDs or LOYALTY- format for new cards.'
        }),
        ('User Assignment', {
            'fields': ('user',),
            'description': 'Assign a user to activate this card. Leave empty to keep it unassigned.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_scan'),
            'classes': ('collapse',)
        }),
        ('QR Code URL', {
            'fields': ('google_script_url',),
            'classes': ('collapse',)
        }),
    )
    
    def user_display(self, obj):
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return format_html('<span style="color: #999;">Unassigned</span>')
    user_display.short_description = 'User'
    
    def status_display(self, obj):
        if not obj.user:
            return format_html('<span style="color: #999;">Unassigned</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')
    status_display.short_description = 'Status'
    
    def google_url_display(self, obj):
        if obj.google_script_url:
            return format_html('<a href="{}" target="_blank">View URL</a>', obj.google_script_url)
        return '-'
    google_url_display.short_description = 'QR URL'
    
    def link_to_user(self, request, queryset):
        """Custom action to link cards to users."""
        if queryset.count() != 1:
            messages.error(request, 'Please select exactly one card to link.')
            return
        
        card = queryset.first()
        if card.user:
            messages.warning(request, f'Card {card.qr_code} is already linked to {card.user.email}')
            return
        
        # Redirect to a custom form to select user
        return HttpResponseRedirect(
            reverse('admin:link_loyalty_card_user', args=[card.id])
        )
    link_to_user.short_description = 'Link to user'
    
    def activate_cards(self, request, queryset):
        """Activate selected cards."""
        count = 0
        for card in queryset:
            if card.activate_card():
                count += 1
        messages.success(request, f'{count} cards activated successfully.')
    activate_cards.short_description = 'Activate selected cards'
    
    def deactivate_cards(self, request, queryset):
        """Deactivate selected cards."""
        count = queryset.update(is_active=False)
        messages.success(request, f'{count} cards deactivated successfully.')
    deactivate_cards.short_description = 'Deactivate selected cards'
    
    def unlink_users(self, request, queryset):
        """Unlink users from selected cards."""
        count = 0
        for card in queryset:
            card.unlink_user()
            count += 1
        messages.success(request, f'{count} cards unlinked from users and deactivated.')
    unlink_users.short_description = 'Unlink users from cards'
    
    def get_queryset(self, request):
        """Filter by business and optimize queryset with user data."""
        qs = super().get_queryset(request).select_related('user', 'restaurant_settings')
        # Filter by business for business admin sites
        if hasattr(self.admin_site, 'get_business_settings'):
            business_settings = self.admin_site.get_business_settings()
            if business_settings:
                return qs.filter(restaurant_settings=business_settings)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Custom save method to handle QR code validation and business assignment."""
        # Auto-assign business if not set (for business admin sites)
        if not change and not obj.restaurant_settings:
            if hasattr(self.admin_site, 'get_business_settings'):
                business_settings = self.admin_site.get_business_settings()
                if business_settings:
                    obj.restaurant_settings = business_settings
        
        if not change:  # New object
            if obj.qr_code and obj.qr_code.isdigit():
                # Check if customer ID already exists for this business
                if obj.restaurant_settings and LoyaltyCard.objects.filter(
                    qr_code=obj.qr_code,
                    restaurant_settings=obj.restaurant_settings
                ).exists():
                    messages.warning(request, f'Customer ID {obj.qr_code} already exists for this business.')
                else:
                    messages.success(request, f'Loyalty card created with customer ID {obj.qr_code}')
            elif obj.qr_code and obj.qr_code.startswith('LOYALTY-'):
                messages.success(request, f'Loyalty card created with QR code {obj.qr_code}')
        
        super().save_model(request, obj, form, change)


class UserPointsAdmin(BusinessAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'restaurant_settings', 'balance', 'total_earned', 'total_spent', 'created_at', 'updated_at']
    list_filter = ['restaurant_settings', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['balance', 'total_earned', 'total_spent', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Filter by business and optimize queryset."""
        qs = super().get_queryset(request).select_related('user', 'restaurant_settings')
        # Filter by business for business admin sites
        if hasattr(self.admin_site, 'get_business_settings'):
            business_settings = self.admin_site.get_business_settings()
            if business_settings:
                return qs.filter(restaurant_settings=business_settings)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Auto-assign business if not set."""
        if not change and not obj.restaurant_settings:
            if hasattr(self.admin_site, 'get_business_settings'):
                business_settings = self.admin_site.get_business_settings()
                if business_settings:
                    obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)


class PointsTransactionAdmin(BusinessAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'restaurant_settings', 'amount_display', 'transaction_type', 'reason', 'balance_after', 'created_at']
    list_filter = ['restaurant_settings', 'transaction_type', 'created_at']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['created_at', 'balance_after']
    date_hierarchy = 'created_at'
    
    def amount_display(self, obj):
        if obj.amount > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.amount)
        else:
            return format_html('<span style="color: red;">{}</span>', obj.amount)
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        """Filter by business and optimize queryset."""
        qs = super().get_queryset(request).select_related('user', 'restaurant_settings')
        # Filter by business for business admin sites
        if hasattr(self.admin_site, 'get_business_settings'):
            business_settings = self.admin_site.get_business_settings()
            if business_settings:
                return qs.filter(restaurant_settings=business_settings)
        return qs


class RewardAdmin(BusinessAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'restaurant_settings', 'points_required', 'reward_type', 'is_active', 'created_at']
    list_filter = ['restaurant_settings', 'is_active', 'reward_type', 'created_at']
    search_fields = ['name', 'description', 'restaurant_settings__name']
    
    fieldsets = (
        ('Business', {
            'fields': ('restaurant_settings',)
        }),
        ('Reward Information', {
            'fields': ('name', 'description', 'reward_type', 'points_required')
        }),
        ('Reward Details', {
            'fields': ('discount_percentage', 'discount_amount', 'free_item')
        }),
        ('Status', {
            'fields': ('is_active', 'max_redemptions', 'current_redemptions')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until')
        }),
    )
    
    def get_queryset(self, request):
        """Filter rewards by business if not superuser."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            from core.utils import get_business_from_request
            restaurant_settings = get_business_from_request(request)
            return qs.filter(restaurant_settings=restaurant_settings)
        except ValueError:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        """Set restaurant_settings if not set and user is not superuser."""
        if not change and not obj.restaurant_settings:
            try:
                from core.utils import get_business_from_request
                restaurant_settings = get_business_from_request(request)
                obj.restaurant_settings = restaurant_settings
            except ValueError:
                pass  # Let it fail validation if business can't be identified
        super().save_model(request, obj, form, change)


class UserRewardAdmin(BusinessAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'reward', 'restaurant_settings', 'points_spent', 'status', 'redeemed_at', 'expires_at', 'used_at']
    list_filter = ['restaurant_settings', 'status', 'redeemed_at', 'expires_at']
    search_fields = ['user__email', 'reward__name']
    readonly_fields = ['redeemed_at']
    
    def get_queryset(self, request):
        """Filter by business and optimize queryset."""
        qs = super().get_queryset(request).select_related('user', 'reward', 'restaurant_settings')
        # Filter by business for business admin sites
        if hasattr(self.admin_site, 'get_business_settings'):
            business_settings = self.admin_site.get_business_settings()
            if business_settings:
                return qs.filter(restaurant_settings=business_settings)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Auto-assign business if not set (derive from reward if available)."""
        if not change and not obj.restaurant_settings:
            if obj.reward and obj.reward.restaurant_settings:
                obj.restaurant_settings = obj.reward.restaurant_settings
            elif hasattr(self.admin_site, 'get_business_settings'):
                business_settings = self.admin_site.get_business_settings()
                if business_settings:
                    obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        """Custom form to show default expiration date."""
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # New object
            form.base_fields['expires_at'].help_text = (
                'Default: 30 days from now. Leave blank to use default.'
            )
        return form

# Register loyalty models with Chopsticks admin only (QR and loyalty features)
chopsticks_admin_site.register(LoyaltyCard, LoyaltyCardAdmin)
chopsticks_admin_site.register(UserPoints, UserPointsAdmin)
chopsticks_admin_site.register(PointsTransaction, PointsTransactionAdmin)
chopsticks_admin_site.register(Reward, RewardAdmin)
chopsticks_admin_site.register(UserReward, UserRewardAdmin)
