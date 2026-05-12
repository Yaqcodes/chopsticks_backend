"""
Multi-tenant admin sites for business-specific administration.

Each business has its own admin site with:
- Custom branding
- Business-specific data filtering
- User access control (only linked users or superusers)
"""

from django.conf import settings
from django.template.response import TemplateResponse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from unfold.sites import UnfoldAdminSite
from .models import RestaurantSettings


class BusinessAdminSite(UnfoldAdminSite):
    """
    Base class for business-specific admin sites.
    
    Provides:
    - Business identification from URL prefix
    - User access control (only linked users or superusers)
    - Business-specific data filtering
    - Custom branding per business
    """
    
    def __init__(self, name, business_identifier, site_title, site_header, index_title, **kwargs):
        """
        Initialize business admin site.
        
        Args:
            name: Admin site name (e.g., 'roschi_admin')
            business_identifier: String to identify business (e.g., 'roschi', 'chopsticks')
            site_title: Admin site title
            site_header: Admin site header
            index_title: Dashboard title
        """
        super().__init__(name=name, **kwargs)
        self.business_identifier = business_identifier
        self.site_title = site_title
        self.site_header = site_header
        self.index_title = index_title
        self._original_unfold = getattr(settings, 'UNFOLD', {})
    
    def get_business_settings(self):
        """
        Get business settings for this admin site.
        
        Uses flexible matching:
        1. Try domain containing business identifier
        2. Try name containing business identifier (case-insensitive)
        3. Returns None if no match found
        """
        # Try domain match (flexible - handles various domain formats)
        business_settings = RestaurantSettings.objects.filter(
            domain__icontains=self.business_identifier
        ).first()
        if business_settings:
            return business_settings
        
        # Fallback: try to get by name (case-insensitive)
        business_settings = RestaurantSettings.objects.filter(
            name__icontains=self.business_identifier.capitalize()
        ).first()
        if business_settings:
            return business_settings
        
        # If still no match, return None (admin will show empty tables)
        return None
    
    def get_roschi_settings(self):
        """
        Legacy method name for backward compatibility.
        Redirects to get_business_settings().
        """
        return self.get_business_settings()
    
    def has_permission(self, request):
        """
        Check if user has permission to access this admin site.
        
        Rules:
        - Superusers can access all business admin sites
        - Staff users must be linked to this business
        - Non-staff users cannot access
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusers can access all business admin sites
        if request.user.is_superuser:
            return True
        
        # Must be staff
        if not request.user.is_staff:
            return False
        
        # Get business settings for this admin site
        business_settings = self.get_business_settings()
        if not business_settings:
            # If business not found, only superusers can access
            return False
        
        # Check if user is linked to this business
        return request.user.has_business_access(business_settings)
    
    def login(self, request, extra_context=None):
        """
        Override login to check business access after authentication.
        """
        # If already authenticated, check permission immediately
        if request.user.is_authenticated:
            if not self.has_permission(request):
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(
                    request,
                    f"You don't have permission to access {self.site_header}. "
                    f"Please contact an administrator to grant you access."
                )
                return redirect('admin:index')  # Redirect to main admin
        
        # Call parent login (handles authentication)
        return super().login(request, extra_context)
    
    def index(self, request, extra_context=None):
        """Override index to use custom template and check permissions."""
        # Check permission
        if not self.has_permission(request):
            # Redirect to login or show error
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    login_url=reverse(f'{self.name}:login'),
                    redirect_field_name=REDIRECT_FIELD_NAME
                )
            else:
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(
                    request,
                    f"You don't have permission to access {self.site_header}. "
                    f"Please contact an administrator to grant you access."
                )
                return redirect('admin:index')
        
        # Get base context from each_context
        context = self.each_context(request)
        
        # Add index-specific context
        context.update({
            'title': self.index_title,
            'app_list': self.get_app_list(request),
        })
        
        # Merge any extra context
        if extra_context:
            context.update(extra_context)
        
        request.current_app = self.name
        
        return TemplateResponse(
            request,
            f'admin/{self.name}/index.html',
            context
        )
    
    def has_module_permission(self, request):
        """
        Check if user has permission to view any models in this admin site.
        
        This is called by Django admin to determine if the app should appear
        in the admin index. We delegate to has_permission.
        """
        return self.has_permission(request)
    
    def each_context(self, request):
        """Override context to inject business-specific Unfold settings."""
        # Get business-specific Unfold settings from settings
        business_unfold_key = f'{self.business_identifier.upper()}_UNFOLD'
        business_unfold = getattr(settings, business_unfold_key, {})
        base_unfold = self._original_unfold.copy()
        
        # Merge business settings over base settings
        merged_unfold = {**base_unfold, **business_unfold}
        
        # Temporarily override settings.UNFOLD
        original_unfold_value = settings.UNFOLD
        settings.UNFOLD = merged_unfold
        
        try:
            context = super().each_context(request)
            # Ensure our site branding is in context
            context['site_title'] = merged_unfold.get('SITE_TITLE', self.site_title)
            context['site_header'] = merged_unfold.get('SITE_HEADER', self.site_header)
            return context
        finally:
            # Restore original UNFOLD settings
            settings.UNFOLD = original_unfold_value


class RoschiWaterAdminSite(BusinessAdminSite):
    """Custom admin site for Roschi Water management."""
    
    def __init__(self, name='roschi_admin', **kwargs):
        super().__init__(
            name=name,
            business_identifier='roschi',
            site_title="Roschi Water Admin",
            site_header="Roschi Water",
            index_title="Dashboard",
            **kwargs
        )


class ChopsticksAdminSite(BusinessAdminSite):
    """Custom admin site for Chopsticks & Bowls management."""
    
    def __init__(self, name='chopsticks_admin', **kwargs):
        super().__init__(
            name=name,
            business_identifier='chopsticks',
            site_title="Chopsticks & Bowls Admin",
            site_header="Chopsticks & Bowls",
            index_title="Dashboard",
            **kwargs
        )


class ZmallAdminSite(BusinessAdminSite):
    """Custom admin site for Zmall (clothing & apparel) management."""
    
    def __init__(self, name='zmall_admin', **kwargs):
        super().__init__(
            name=name,
            business_identifier='zmall',
            site_title="Zmall Admin",
            site_header="Zmall",
            index_title="Dashboard",
            **kwargs
        )


# Create admin site instances
roschi_admin_site = RoschiWaterAdminSite(name='roschi_admin')
chopsticks_admin_site = ChopsticksAdminSite(name='chopsticks_admin')
zmall_admin_site = ZmallAdminSite(name='zmall_admin')

# Ensure branding is set correctly
roschi_admin_site.site_title = "Roschi Water Admin"
roschi_admin_site.site_header = "Roschi Water"
roschi_admin_site.index_title = "Dashboard"

chopsticks_admin_site.site_title = "Chopsticks & Bowls Admin"
chopsticks_admin_site.site_header = "Chopsticks & Bowls"
chopsticks_admin_site.index_title = "Dashboard"

zmall_admin_site.site_title = "Zmall Admin"
zmall_admin_site.site_header = "Zmall"
zmall_admin_site.index_title = "Dashboard"
