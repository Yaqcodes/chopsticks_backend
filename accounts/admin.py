from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.forms import DateInput
from .models import User, SocialAccount


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin interface."""
    
    list_display = ['email', 'username', 'first_name', 'last_name', 'phone', 'referral_code', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined', 'date_of_birth']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone', 'referral_code']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'avatar', 'date_of_birth', 'referral_code', 'referred_by')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'avatar', 'date_of_birth', 'referral_code', 'referred_by')
        }),
    )
    
    readonly_fields = ['referral_code', 'date_joined']
    
    # Customize date field display
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'date_of_birth' in form.base_fields:
            # Force the widget to be a date input
            form.base_fields['date_of_birth'].widget = DateInput(attrs={
                'type': 'date',
                'class': 'vDateField'
            })
        return form


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """Social Account admin interface."""
    
    list_display = ['user', 'provider', 'provider_user_id', 'created_at']
    list_filter = ['provider', 'created_at']
    search_fields = ['user__email', 'user__username', 'provider_user_id']
    ordering = ['-created_at']
    
    readonly_fields = ['created_at', 'updated_at']
