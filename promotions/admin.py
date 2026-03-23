from django.contrib import admin
from core.utils import get_business_from_request
from .models import PromoCode, PromoCodeUsage


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """Admin interface for PromoCode model (multi-tenant)."""
    
    list_display = [
        'code', 'restaurant_settings', 'discount_type', 'discount_value', 'is_active', 
        'current_usage', 'is_valid', 'created_at'
    ]
    list_filter = ['restaurant_settings', 'discount_type', 'is_active', 'valid_from', 'valid_until', 'created_at']
    search_fields = ['code', 'description', 'restaurant_settings__name']
    ordering = ['-created_at']
    readonly_fields = ['current_usage', 'created_at']
    
    fieldsets = (
        ('Business', {
            'fields': ('restaurant_settings',)
        }),
        ('Basic Information', {
            'fields': ('code', 'description', 'discount_type', 'discount_value')
        }),
        ('Usage Limits', {
            'fields': ('minimum_order_amount', 'maximum_discount', 'usage_limit', 'current_usage')
        }),
        ('Validity', {
            'fields': ('is_active', 'valid_from', 'valid_until')
        }),
    )
    
    def get_queryset(self, request):
        """Filter promo codes by business if not superuser."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            restaurant_settings = get_business_from_request(request)
            return qs.filter(restaurant_settings=restaurant_settings)
        except ValueError:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        """Set restaurant_settings if not set and user is not superuser."""
        if not change and not obj.restaurant_settings:
            try:
                restaurant_settings = get_business_from_request(request)
                obj.restaurant_settings = restaurant_settings
            except ValueError:
                pass  # Let it fail validation if business can't be identified
        super().save_model(request, obj, form, change)
    
    actions = ['activate_promo_codes', 'deactivate_promo_codes']
    
    def activate_promo_codes(self, request, queryset):
        """Activate selected promotional codes."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotional codes activated.')
    activate_promo_codes.short_description = "Activate selected promotional codes"
    
    def deactivate_promo_codes(self, request, queryset):
        """Deactivate selected promotional codes."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotional codes deactivated.')
    deactivate_promo_codes.short_description = "Deactivate selected promotional codes"


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    """Admin interface for PromoCodeUsage model."""
    
    list_display = [
        'promo_code', 'user', 'order', 'discount_amount', 'used_at'
    ]
    list_filter = ['used_at', 'promo_code__discount_type']
    search_fields = [
        'promo_code__code', 'user__email', 'user__username', 'order__order_number'
    ]
    ordering = ['-used_at']
    readonly_fields = ['used_at']
    
    fieldsets = (
        ('Usage Details', {
            'fields': ('promo_code', 'user', 'order', 'discount_amount')
        }),
        ('Timestamps', {
            'fields': ('used_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('promo_code', 'user', 'order')
