from django.contrib import admin
from unfold.admin import ModelAdmin
from core.utils import get_business_from_request
from core.admin_sites import zmall_admin_site
from core.main_admin_site import main_admin_site
from .models import PromoCode, PromoCodeUsage


class BusinessAdminMixin:
    """Permission helpers for tenant-scoped admin sites."""

    def has_module_permission(self, request):
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff

    def has_add_permission(self, request):
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff

    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class PromoCodeAdmin(ModelAdmin):
    """Superuser admin: all tenants."""

    list_display = [
        'code', 'restaurant_settings', 'discount_type', 'discount_value', 'is_active',
        'current_usage', 'is_valid', 'created_at',
    ]
    list_filter = ['restaurant_settings', 'discount_type', 'is_active', 'valid_from', 'valid_until', 'created_at']
    search_fields = ['code', 'description', 'restaurant_settings__name']
    ordering = ['-created_at']
    readonly_fields = ['current_usage', 'created_at']
    actions = ['activate_promo_codes', 'deactivate_promo_codes']

    fieldsets = (
        ('Business', {'fields': ('restaurant_settings',)}),
        ('Basic Information', {'fields': ('code', 'description', 'discount_type', 'discount_value')}),
        ('Usage Limits', {'fields': ('minimum_order_amount', 'maximum_discount', 'usage_limit', 'current_usage')}),
        ('Validity', {'fields': ('is_active', 'valid_from', 'valid_until')}),
    )

    def activate_promo_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotional codes activated.')
    activate_promo_codes.short_description = 'Activate selected promotional codes'

    def deactivate_promo_codes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotional codes deactivated.')
    deactivate_promo_codes.short_description = 'Deactivate selected promotional codes'


class ZmallPromoCodeAdmin(BusinessAdminMixin, ModelAdmin):
    """Zmall admin: business-scoped promo code management."""

    list_display = [
        'code', 'discount_type', 'discount_value', 'minimum_order_amount',
        'is_active', 'current_usage', 'usage_limit', 'valid_until',
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    ordering = ['-created_at']
    readonly_fields = ['current_usage', 'created_at']
    actions = ['activate_promo_codes', 'deactivate_promo_codes']

    fieldsets = (
        ('Basic Information', {'fields': ('code', 'description', 'discount_type', 'discount_value')}),
        ('Usage Limits', {'fields': ('minimum_order_amount', 'maximum_discount', 'usage_limit', 'current_usage')}),
        ('Validity', {'fields': ('is_active', 'valid_from', 'valid_until')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if not business_settings:
            return qs.none()
        return qs.filter(restaurant_settings=business_settings)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if self._get_business_settings():
            return fieldsets
        return PromoCodeAdmin.fieldsets

    def save_model(self, request, obj, form, change):
        if not obj.restaurant_settings_id:
            obj.restaurant_settings = self._get_business_settings()
        if obj.code:
            obj.code = obj.code.strip().upper()
        super().save_model(request, obj, form, change)

    def activate_promo_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotional codes activated.')
    activate_promo_codes.short_description = 'Activate selected promotional codes'

    def deactivate_promo_codes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotional codes deactivated.')
    deactivate_promo_codes.short_description = 'Deactivate selected promotional codes'


class PromoCodeUsageAdmin(ModelAdmin):
    list_display = ['promo_code', 'user', 'guest_email', 'order', 'discount_amount', 'used_at']
    list_filter = ['used_at', 'promo_code__discount_type']
    search_fields = ['promo_code__code', 'user__email', 'guest_email', 'order__order_number']
    ordering = ['-used_at']
    readonly_fields = ['promo_code', 'user', 'guest_email', 'order', 'discount_amount', 'used_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('promo_code', 'user', 'order')


class ZmallPromoCodeUsageAdmin(BusinessAdminMixin, PromoCodeUsageAdmin):
    list_display = ['promo_code', 'user', 'guest_email', 'order', 'discount_amount', 'used_at']
    search_fields = ['promo_code__code', 'user__email', 'guest_email', 'order__order_number']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if not business_settings:
            return qs.none()
        return qs.filter(promo_code__restaurant_settings=business_settings)


zmall_admin_site.register(PromoCode, ZmallPromoCodeAdmin)
zmall_admin_site.register(PromoCodeUsage, ZmallPromoCodeUsageAdmin)
main_admin_site.register(PromoCode, PromoCodeAdmin)
main_admin_site.register(PromoCodeUsage, PromoCodeUsageAdmin)
