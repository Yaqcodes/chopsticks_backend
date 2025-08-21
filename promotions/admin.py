from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import PromoCode, PromoCodeUsage


@admin.register(PromoCode)
class PromoCodeAdmin(UnfoldModelAdmin):
    """Admin interface for PromoCode model."""
    
    list_display = [
        'code', 'discount_type', 'discount_value', 'is_active', 
        'current_usage', 'is_valid', 'created_at'
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until', 'created_at']
    search_fields = ['code', 'description']
    ordering = ['-created_at']
    readonly_fields = ['current_usage', 'created_at']
    
    fieldsets = (
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
class PromoCodeUsageAdmin(UnfoldModelAdmin):
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
