from django.conf import settings
from django.template.response import TemplateResponse
from unfold.sites import UnfoldAdminSite
from .models import RestaurantSettings


class RoschiWaterAdminSite(UnfoldAdminSite):
    """Custom Unfold admin site for Roschi Water management."""
    
    site_title = "Roschi Water Admin"
    site_header = "Roschi Water"
    index_title = "Dashboard"
    
    def __init__(self, name='roschi_admin', **kwargs):
        super().__init__(name=name, **kwargs)
        # Store original UNFOLD settings
        self._original_unfold = getattr(settings, 'UNFOLD', {})
    
    def index(self, request, extra_context=None):
        """Override index to use custom template without QR/loyalty references."""
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
            'admin/roschi_admin/index.html',
            context
        )
    
    def each_context(self, request):
        """Override context to inject Roschi-specific Unfold settings."""
        # Temporarily patch UNFOLD settings for this request
        roschi_unfold = getattr(settings, 'ROSCHI_UNFOLD', {})
        base_unfold = self._original_unfold.copy()
        
        # Merge Roschi settings over base settings
        merged_unfold = {**base_unfold, **roschi_unfold}
        
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
    
    def get_roschi_settings(self):
        """
        Get Roschi Water BusinessSettings instance.
        
        Uses flexible matching:
        1. Try domain containing 'roschiwater' or 'roschi'
        2. Try name containing 'Roschi' (case-insensitive)
        3. Returns None if no match found
        """
        # Try domain match (flexible - handles roschiwater.com, api.roschiwater.com, etc.)
        roschi_settings = RestaurantSettings.objects.filter(
            domain__icontains='roschi'
        ).first()
        if roschi_settings:
            return roschi_settings
        
        # Fallback: try to get by name (case-insensitive)
        roschi_settings = RestaurantSettings.objects.filter(
            name__icontains='Roschi'
        ).first()
        if roschi_settings:
            return roschi_settings
        
        # If still no match, return None (admin will show empty tables)
        return None


# Create custom admin site instance with Unfold
roschi_admin_site = RoschiWaterAdminSite(name='roschi_admin')

# Ensure branding is set correctly
roschi_admin_site.site_title = "Roschi Water Admin"
roschi_admin_site.site_header = "Roschi Water"
roschi_admin_site.index_title = "Dashboard"
