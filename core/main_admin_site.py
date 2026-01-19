"""
Main admin site restricted to superusers only.

This is the system-wide admin for managing all tenants and system-level settings.
Only superusers can access this admin.
"""

from django.contrib import admin
from unfold.sites import UnfoldAdminSite


class MainAdminSite(UnfoldAdminSite):
    """
    Main admin site restricted to superusers only.
    
    This admin is for system-wide management across all tenants.
    Only superusers can access this admin.
    """
    
    def has_permission(self, request):
        """
        Restrict access to superusers only.
        
        Rules:
        - Only superusers can access
        - All other users are denied access
        """
        if not request.user.is_authenticated:
            return False
        
        # Only superusers can access the main admin
        return request.user.is_superuser
    
    def index(self, request, extra_context=None):
        """Override index to check superuser permission."""
        if not self.has_permission(request):
            from django.contrib import messages
            from django.shortcuts import redirect
            from django.contrib.auth import REDIRECT_FIELD_NAME
            from django.contrib.auth.views import redirect_to_login
            from django.urls import reverse
            
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    login_url=reverse('admin:login'),
                    redirect_field_name=REDIRECT_FIELD_NAME
                )
            else:
                messages.error(
                    request,
                    "You don't have permission to access the main admin. "
                    "Only superusers can access this admin. "
                    "Please use your business-specific admin panel instead."
                )
                # Redirect to a business admin if user has access, otherwise logout
                if request.user.is_staff:
                    # Try to redirect to a business admin the user has access to
                    accessible_businesses = request.user.get_accessible_businesses()
                    if accessible_businesses.exists():
                        # Redirect to first accessible business admin
                        business = accessible_businesses.first()
                        if business:
                            domain = (business.domain or '').lower()
                            name = (business.name or '').lower()
                            if 'roschi' in domain or 'roschi' in name:
                                return redirect('/roschi-admin/')
                            elif 'chopsticks' in domain or 'chopsticks' in name:
                                return redirect('/cb-admin/')
                
                return redirect('/')
        
        return super().index(request, extra_context)


# Create main admin site instance
main_admin_site = MainAdminSite(name='admin')
main_admin_site.site_title = "Tenant Administration"
main_admin_site.site_header = "Tenant Administration"
main_admin_site.index_title = "Administration"
