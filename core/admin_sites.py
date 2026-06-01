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

_BUSINESS_SETTINGS_UNSET = object()


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
    
    def clear_business_settings_cache(self, request=None):
        """Drop per-request tenant cache (e.g. after saving business settings)."""
        if request is not None:
            for attr in ('_business_admin_settings', '_business_admin_settings_resolved'):
                if hasattr(request, attr):
                    delattr(request, attr)

    def _business_settings_queryset(self, request=None):
        """Candidates for this admin site; staff are limited to linked businesses."""
        qs = RestaurantSettings.objects.all()
        if request and request.user.is_authenticated and not request.user.is_superuser:
            qs = qs.filter(id__in=request.user.businesses.values_list('id', flat=True))
        return qs

    def get_business_settings(self, request=None):
        """
        Resolve RestaurantSettings for this admin site.

        Uses flexible matching on domain/name containing business_identifier.
        Staff users only see tenants they are linked to. Cached on the request only
        (not on the admin site singleton) so saves are visible on the next page load.
        """
        if request is not None and getattr(request, '_business_admin_settings_resolved', False):
            cached = getattr(request, '_business_admin_settings', _BUSINESS_SETTINGS_UNSET)
            if cached is not _BUSINESS_SETTINGS_UNSET:
                return cached if cached is not None else None

        qs = self._business_settings_queryset(request)
        identifier = self.business_identifier

        business_settings = (
            qs.filter(domain__icontains=identifier).order_by('pk').first()
        )
        if not business_settings:
            business_settings = (
                qs.filter(name__icontains=identifier.capitalize()).order_by('pk').first()
            )

        if request is not None:
            request._business_admin_settings_resolved = True
            request._business_admin_settings = business_settings

        return business_settings
    
    def get_roschi_settings(self, request=None):
        """
        Legacy method name for backward compatibility.
        Redirects to get_business_settings().
        """
        return self.get_business_settings(request)
    
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
        business_settings = self.get_business_settings(request)
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
        self.clear_business_settings_cache(request)

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
