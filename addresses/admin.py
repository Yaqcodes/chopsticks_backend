from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Address


@admin.register(Address)
class AddressAdmin(UnfoldModelAdmin):
    """Admin interface for Address model."""
    
    list_display = ['user', 'full_name', 'address_type', 'city', 'state', 'is_default', 'created_at']
    list_filter = ['address_type', 'is_default', 'country', 'created_at']
    search_fields = ['user__email', 'user__username', 'full_name', 'address', 'city', 'state']
    ordering = ['-created_at']
    list_editable = ['is_default', 'address_type']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'phone')
        }),
        ('Address Details', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Location & Settings', {
            'fields': ('latitude', 'longitude', 'is_default', 'address_type')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')
