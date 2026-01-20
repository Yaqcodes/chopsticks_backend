from django.contrib import admin
from django.shortcuts import render
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import RestaurantSettings, Quote
from .admin_sites import roschi_admin_site, chopsticks_admin_site
from .main_admin_site import main_admin_site


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    """Admin interface for RestaurantSettings model."""
    
    list_display = ['name', 'domain', 'restaurant_coordinates', 'delivery_radius', 'is_open', 'updated_at']
    list_editable = ['delivery_radius', 'is_open']
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['name', 'address', 'phone', 'email']
    list_filter = ['is_open', 'maintenance_mode', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    save_on_top = True
    save_as_continue = False
    
    # Customize field labels and help text
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'address', 'phone', 'email', 'website', 'domain')
        }),
        ('Paystack Configuration', {
            'fields': ('paystack_secret_key', 'paystack_public_key', 'paystack_webhook_secret'),
            'classes': ('collapse',)
        }),
        ('Restaurant Location', {
            'fields': ('restaurant_latitude', 'restaurant_longitude'),
            'description': 'Coordinates for accurate distance calculations and delivery fee computation. Use decimal degrees format (e.g., 9.05509, 7.44056 for Wuye Branch). Coordinates are validated to be within Nigeria bounds.'
        }),
        ('Operating Hours', {
            'fields': ('opening_time', 'closing_time', 'is_open')
        }),
        ('Delivery Settings', {
            'fields': (
                'delivery_radius', 
                'minimum_order', 
                'free_delivery_threshold',
                'vat_rate'
            ),
            'description': 'Configure delivery radius, minimum order, and tax rate.'
        }),
        ('Payment Methods', {
            'fields': ('accepts_cash', 'accepts_card', 'accepts_mobile_money')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url')
        }),
        ('Branding', {
            'fields': ('logo', 'favicon')
        }),
        ('SEO & Meta', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('System Settings', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'classes': ('collapse',)
        }),
    )
    
    actions = []
    
    def has_add_permission(self, request):
        """Only allow one settings instance."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of restaurant settings."""
        return False

    def get_form(self, request, obj=None, **kwargs):
        """Custom form with enhanced help text."""
        form = super().get_form(request, obj, **kwargs)
        
        if form.base_fields.get('delivery_radius'):
            form.base_fields['delivery_radius'].help_text = (
                'Maximum delivery distance in kilometers. Orders beyond this radius cannot be delivered.'
            )
        
        # Add helpful text for coordinate fields
        if form.base_fields.get('restaurant_latitude'):
            form.base_fields['restaurant_latitude'].help_text = (
                'Restaurant latitude in decimal degrees (e.g., 9.0820 for Abuja). Use negative values for South, positive for North.'
            )
        
        if form.base_fields.get('restaurant_longitude'):
            form.base_fields['restaurant_longitude'].help_text = (
                'Restaurant longitude in decimal degrees (e.g., 7.3986 for Abuja). Use negative values for West, positive for East.'
            )
        
        return form
    
    def restaurant_coordinates(self, obj):
        """Display restaurant coordinates in a readable format."""
        coords = obj.coordinates_display
        if coords != "Not set":
            # Add a link to open in Google Maps
            google_maps_url = f"https://www.google.com/maps?q={obj.restaurant_latitude},{obj.restaurant_longitude}"
            return f'<a href="{google_maps_url}" target="_blank">{coords}</a>'
        return coords
    restaurant_coordinates.short_description = "Coordinates"
    restaurant_coordinates.allow_tags = True
    
    


# Business Admin Mixin for permissions
class BusinessAdminMixin:
    """
    Mixin to add permission methods for business admin classes.
    
    Ensures that staff users linked to the business can view and manage models.
    Also provides dashboard-style redirect for single-record models.
    """
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to change view if there's only one object (dashboard-style interface)."""
        queryset = self.get_queryset(request)
        if queryset.count() == 1:
            obj = queryset.first()
            from django.shortcuts import redirect
            return redirect(f'{obj.pk}/change/')
        return super().changelist_view(request, extra_context)
    
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


# Roschi Water Admin Class - Business Settings
class RoschiBusinessSettingsAdmin(BusinessAdminMixin, ModelAdmin):
    """Business Settings - Configure how your business operates, accepts payments, and delivers orders."""
    
    # Remove list_display and list_editable since we'll redirect to change view
    list_display = ['name', 'tagline', 'phone', 'email', 'is_open', 'last_updated']
    list_display_links = ['name']
    readonly_fields = ['created_at', 'updated_at', 'domain']
    search_fields = ['name', 'tagline', 'address', 'phone', 'email', 'website', 'description']
    list_filter = ['is_open', 'accepts_cash', 'accepts_card', 'accepts_mobile_money', 'updated_at']
    ordering = ['-updated_at']
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to change view if there's only one business settings object."""
        queryset = self.get_queryset(request)
        if queryset.count() == 1:
            obj = queryset.first()
            from django.shortcuts import redirect
            return redirect(f'{obj.pk}/change/')
        return super().changelist_view(request, extra_context)
    
    fieldsets = (
        ('About Your Business', {
            'fields': ('name', 'tagline', 'description', 'address', 'phone', 'email', 'website', 'domain'),
            'description': 'Basic information that customers will see about your business'
        }),
        ('Branding', {
            'fields': ('logo', 'favicon'),
            'description': 'Upload your business logo and favicon'
        }),
        ('Payment Setup', {
            'fields': ('paystack_secret_key', 'paystack_public_key', 'paystack_webhook_secret'),
            'description': 'Paystack payment account settings. Get these from your Paystack dashboard. Contact support if you need help.'
        }),
        ('Your Business Location', {
            'fields': ('restaurant_latitude', 'restaurant_longitude'),
            'description': 'Your business address coordinates. Used to calculate delivery distances and fees. You can find these on Google Maps.'
        }),
        ('When Are You Open?', {
            'fields': ('opening_time', 'closing_time', 'is_open', 'opening_hours'),
            'description': 'When customers can place orders'
        }),
        ('Pricing', {
            'fields': (
                'minimum_order', 
                'vat_rate'
            ),
            'description': 'Set minimum order amount and tax rate (VAT).'
        }),
        ('Social Media Links', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url'),
            'description': 'Links to your social media pages (optional)'
        }),
        ('SEO & Meta Information', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'description': 'SEO settings for search engines (optional)',
            'classes': ('collapse',)
        }),
        ('System Settings', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'description': 'Temporarily disable your site for maintenance',
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Add user-friendly help text to form fields."""
        form = super().get_form(request, obj, **kwargs)
        
        # Update field labels and help text
        if 'name' in form.base_fields:
            form.base_fields['name'].label = 'Business Name'
            form.base_fields['name'].help_text = 'Your business name (e.g., "Roschi Water")'
        
        if 'description' in form.base_fields:
            form.base_fields['description'].label = 'Business Description'
            form.base_fields['description'].help_text = 'A short description of your business'
        
        if 'address' in form.base_fields:
            form.base_fields['address'].label = 'Business Address'
            form.base_fields['address'].help_text = 'Your business physical address'
        
        if 'phone' in form.base_fields:
            form.base_fields['phone'].label = 'Phone Number'
            form.base_fields['phone'].help_text = 'Contact phone number for your business'
        
        if 'email' in form.base_fields:
            form.base_fields['email'].label = 'Email Address'
            form.base_fields['email'].help_text = 'Contact email for your business'
        
        if 'website' in form.base_fields:
            form.base_fields['website'].label = 'Website URL'
            form.base_fields['website'].help_text = 'Your business website (if you have one)'
        
        if 'tagline' in form.base_fields:
            form.base_fields['tagline'].label = 'Tagline'
            form.base_fields['tagline'].help_text = 'A short catchy phrase about your business (e.g., "Pure by nature, bottled at source")'
        
        if 'logo' in form.base_fields:
            form.base_fields['logo'].label = 'Business Logo'
            form.base_fields['logo'].help_text = 'Upload your business logo (will be displayed in the footer and other places)'
        
        if 'favicon' in form.base_fields:
            form.base_fields['favicon'].label = 'Favicon'
            form.base_fields['favicon'].help_text = 'Small icon displayed in browser tabs (optional)'
        
        if 'free_delivery_threshold' in form.base_fields:
            form.base_fields['free_delivery_threshold'].label = 'Free Delivery Threshold (₦)'
            form.base_fields['free_delivery_threshold'].help_text = 'Orders above this amount get free delivery (set to 0 to disable)'
        
        if 'opening_hours' in form.base_fields:
            form.base_fields['opening_hours'].label = 'Opening Hours (JSON)'
            form.base_fields['opening_hours'].help_text = 'Detailed opening hours in JSON format (optional, advanced)'
        
        if 'meta_title' in form.base_fields:
            form.base_fields['meta_title'].label = 'SEO Title'
            form.base_fields['meta_title'].help_text = 'Title shown in search engine results (optional)'
        
        if 'meta_description' in form.base_fields:
            form.base_fields['meta_description'].label = 'SEO Description'
            form.base_fields['meta_description'].help_text = 'Description shown in search engine results (optional)'
        
        if 'meta_keywords' in form.base_fields:
            form.base_fields['meta_keywords'].label = 'SEO Keywords'
            form.base_fields['meta_keywords'].help_text = 'Keywords for search engines (optional, comma-separated)'
        
        if 'maintenance_mode' in form.base_fields:
            form.base_fields['maintenance_mode'].label = 'Maintenance Mode'
            form.base_fields['maintenance_mode'].help_text = 'Enable to temporarily disable your site for maintenance'
        
        if 'maintenance_message' in form.base_fields:
            form.base_fields['maintenance_message'].label = 'Maintenance Message'
            form.base_fields['maintenance_message'].help_text = 'Message shown to users when maintenance mode is enabled'
        
        if 'paystack_secret_key' in form.base_fields:
            form.base_fields['paystack_secret_key'].label = 'Paystack Secret Key'
            form.base_fields['paystack_secret_key'].help_text = 'Get this from your Paystack dashboard under Settings → API Keys & Webhooks'
        
        if 'paystack_public_key' in form.base_fields:
            form.base_fields['paystack_public_key'].label = 'Paystack Public Key'
            form.base_fields['paystack_public_key'].help_text = 'Get this from your Paystack dashboard under Settings → API Keys & Webhooks'
        
        if 'paystack_webhook_secret' in form.base_fields:
            form.base_fields['paystack_webhook_secret'].label = 'Paystack Webhook Secret'
            form.base_fields['paystack_webhook_secret'].help_text = 'Optional: For advanced payment verification. Get from Paystack dashboard.'
        
        if 'restaurant_latitude' in form.base_fields:
            form.base_fields['restaurant_latitude'].label = 'Latitude'
            form.base_fields['restaurant_latitude'].help_text = 'Your business latitude (find on Google Maps by right-clicking your location)'
        
        if 'restaurant_longitude' in form.base_fields:
            form.base_fields['restaurant_longitude'].label = 'Longitude'
            form.base_fields['restaurant_longitude'].help_text = 'Your business longitude (find on Google Maps by right-clicking your location)'
        
        if 'opening_time' in form.base_fields:
            form.base_fields['opening_time'].label = 'Opening Time'
            form.base_fields['opening_time'].help_text = 'What time you start accepting orders (e.g., 08:00)'
        
        if 'closing_time' in form.base_fields:
            form.base_fields['closing_time'].label = 'Closing Time'
            form.base_fields['closing_time'].help_text = 'What time you stop accepting orders (e.g., 22:00)'
        
        if 'is_open' in form.base_fields:
            form.base_fields['is_open'].label = 'Currently Open'
            form.base_fields['is_open'].help_text = 'Turn this off to temporarily stop accepting orders'
        
        if 'delivery_radius' in form.base_fields:
            form.base_fields['delivery_radius'].label = 'Maximum Delivery Distance (km)'
            form.base_fields['delivery_radius'].help_text = 'How far you can deliver (in kilometers). Orders beyond this distance will be rejected.'
        
        if 'minimum_order' in form.base_fields:
            form.base_fields['minimum_order'].label = 'Minimum Order Amount (₦)'
            form.base_fields['minimum_order'].help_text = 'Customers must order at least this amount (set to 0 for no minimum)'
        
        if 'vat_rate' in form.base_fields:
            form.base_fields['vat_rate'].label = 'Tax Rate (VAT)'
            form.base_fields['vat_rate'].help_text = 'Tax percentage as decimal (e.g., 0.075 for 7.5% tax)'
        
        # Payment method fields removed for Roschi - only in ChopsticksBusinessSettingsAdmin
        
        return form
    
    actions = []
    
    def get_queryset(self, request):
        """Show only this business's settings."""
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(id=business_settings.id)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    def has_add_permission(self, request):
        """Only one business settings record allowed."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Cannot delete business settings."""
        return False
    
    def is_open_display(self, obj):
        """Whether business is currently open for orders."""
        if obj.is_open:
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ Open</span>')
        else:
            return format_html('<span style="color: #ef4444; font-weight: bold;">✗ Closed</span>')
    is_open_display.short_description = 'Status'
    
    def last_updated(self, obj):
        """When settings were last changed."""
        return obj.updated_at.strftime('%B %d, %Y')
    last_updated.short_description = 'Last Updated'
    


# Chopsticks & Bowls Admin Class - Business Settings (with QR/Loyalty features)
class ChopsticksBusinessSettingsAdmin(RoschiBusinessSettingsAdmin):
    """Business Settings for Chopsticks & Bowls - includes QR code and loyalty features."""
    
    # Override fieldsets to include Delivery & Pricing and Payment Methods sections
    fieldsets = (
        ('About Your Business', {
            'fields': ('name', 'tagline', 'description', 'address', 'phone', 'email', 'website', 'domain'),
            'description': 'Basic information that customers will see about your business'
        }),
        ('Branding', {
            'fields': ('logo', 'favicon'),
            'description': 'Upload your business logo and favicon'
        }),
        ('Payment Setup', {
            'fields': ('paystack_secret_key', 'paystack_public_key', 'paystack_webhook_secret'),
            'description': 'Paystack payment account settings. Get these from your Paystack dashboard. Contact support if you need help.'
        }),
        ('Your Business Location', {
            'fields': ('restaurant_latitude', 'restaurant_longitude'),
            'description': 'Your business address coordinates. Used to calculate delivery distances and fees. You can find these on Google Maps.'
        }),
        ('When Are You Open?', {
            'fields': ('opening_time', 'closing_time', 'is_open', 'opening_hours'),
            'description': 'When customers can place orders'
        }),
        ('Delivery & Pricing', {
            'fields': (
                'delivery_radius', 
                'minimum_order', 
                'free_delivery_threshold',
                'vat_rate'
            ),
            'description': 'Set delivery radius, minimum order amount, and tax rate.'
        }),
        ('Accepted Payment Methods', {
            'fields': ('accepts_cash', 'accepts_card', 'accepts_mobile_money'),
            'description': 'Choose which payment methods your customers can use'
        }),
        ('Social Media Links', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url'),
            'description': 'Links to your social media pages (optional)'
        }),
        ('SEO & Meta Information', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'description': 'SEO settings for search engines (optional)',
            'classes': ('collapse',)
        }),
        ('System Settings', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'description': 'Temporarily disable your site for maintenance',
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Add user-friendly help text to form fields, including payment methods."""
        form = super().get_form(request, obj, **kwargs)
        
        # Add payment method help text for Chopsticks
        if 'accepts_cash' in form.base_fields:
            form.base_fields['accepts_cash'].label = 'Accept Cash on Delivery'
            form.base_fields['accepts_cash'].help_text = 'Allow customers to pay with cash when order is delivered'
        
        if 'accepts_card' in form.base_fields:
            form.base_fields['accepts_card'].label = 'Accept Card Payments'
            form.base_fields['accepts_card'].help_text = 'Allow customers to pay with debit/credit cards online'
        
        if 'accepts_mobile_money' in form.base_fields:
            form.base_fields['accepts_mobile_money'].label = 'Accept Mobile Money'
            form.base_fields['accepts_mobile_money'].help_text = 'Allow customers to pay with mobile money transfers'
        
        return form
    
    actions = ['reset_delivery_fees', 'enable_free_delivery', 'disable_free_delivery', 'set_nigerian_city_coordinates']
    
    def set_nigerian_city_coordinates(self, request, queryset):
        """Set coordinates for common Nigerian cities (QR code feature)."""
        from django import forms
        
        class CityForm(forms.Form):
            city = forms.ChoiceField(
                choices=[
                    ('abuja', 'Abuja (Federal Capital Territory)'),
                    ('lagos', 'Lagos'),
                    ('kano', 'Kano'),
                    ('ibadan', 'Ibadan'),
                    ('kaduna', 'Kaduna'),
                    ('port_harcourt', 'Port Harcourt'),
                    ('maiduguri', 'Maiduguri'),
                    ('zaria', 'Zaria'),
                    ('bauchi', 'Bauchi'),
                    ('jos', 'Jos'),
                ],
                label='Select City'
            )
        
        if 'apply' in request.POST:
            form = CityForm(request.POST)
            if form.is_valid():
                city = form.cleaned_data['city']
                
                # City coordinates (latitude, longitude)
                city_coordinates = {
                    'abuja': (9.0820, 7.3986),
                    'lagos': (6.5244, 3.3792),
                    'kano': (11.9911, 8.5311),
                    'ibadan': (7.3961, 3.8969),
                    'kaduna': (10.5222, 7.4384),
                    'port_harcourt': (4.8156, 7.0498),
                    'maiduguri': (11.8333, 13.1500),
                    'zaria': (11.1111, 7.7222),
                    'bauchi': (10.3158, 9.8442),
                    'jos': (9.8965, 8.8583),
                }
                
                if city in city_coordinates:
                    lat, lng = city_coordinates[city]
                    count = 0
                    for settings_obj in queryset:
                        settings_obj.restaurant_latitude = lat
                        settings_obj.restaurant_longitude = lng
                        settings_obj.save()
                        count += 1
                    
                    self.message_user(
                        request, 
                        f'Successfully set coordinates for {count} restaurant settings to {city.title()} ({lat}, {lng})'
                    )
                    return
                else:
                    self.message_user(request, 'Invalid city selected.')
                    return
        
        # Show the form
        form = CityForm()
        return render(
            request,
            'admin/core/restaurantsettings/set_city_coordinates.html',
            {
                'title': 'Set Nigerian City Coordinates',
                'form': form,
                'queryset': queryset,
                'opts': self.model._meta,
            }
        )
    set_nigerian_city_coordinates.short_description = "📍 Set coordinates for Nigerian city (QR feature)"


# Quote Admin for Roschi Water
class QuoteAdmin(ModelAdmin):
    """Admin interface for Quote requests (Roschi Water only)."""
    
    # Explicitly set the model
    model = Quote
    
    list_display = [
        'id', 'full_name', 'email', 'phone', 'status_badge', 'created_at', 'message_preview', 'quick_actions'
    ]
    list_filter = ['status', 'created_at', 'restaurant_settings']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at', 'full_name']
    ordering = ['-created_at']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('first_name', 'last_name', 'full_name', 'email', 'phone')
        }),
        ('Quote Details', {
            'fields': ('message', 'status', 'admin_notes')
        }),
        ('Metadata', {
            'fields': ('id', 'restaurant_settings', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter quotes by business for Roschi Water."""
        qs = super().get_queryset(request)
        business_settings = roschi_admin_site.get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        # Return all quotes if no business settings (model should still be visible)
        return qs
    
    def message_preview(self, obj):
        """Show truncated message preview."""
        if obj.message:
            preview = obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
            return format_html('<span title="{}">{}</span>', obj.message, preview)
        return '-'
    message_preview.short_description = 'Message Preview'
    
    def status_badge(self, obj):
        """Display status with colored badge."""
        status_colors = {
            'pending': '#f59e0b',  # Orange
            'reviewed': '#3b82f6',  # Blue
            'responded': '#10b981',  # Green
            'closed': '#6b7280',  # Gray
        }
        color = status_colors.get(obj.status, '#6b7280')
        status_display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">{}</span>',
            color,
            status_display
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def quick_actions(self, obj):
        """Quick action buttons for status updates."""
        actions = []
        if obj.status == 'pending':
            actions.append(
                format_html(
                    '<a href="?action=mark_reviewed&quote_id={}" class="button" style="background: #3b82f6; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 0.75rem;">Review</a>',
                    obj.id
                )
            )
        elif obj.status == 'reviewed':
            actions.append(
                format_html(
                    '<a href="?action=mark_responded&quote_id={}" class="button" style="background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 0.75rem;">Respond</a>',
                    obj.id
                )
            )
        if obj.status != 'closed':
            actions.append(
                format_html(
                    '<a href="?action=mark_closed&quote_id={}" class="button" style="background: #6b7280; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 0.75rem; margin-left: 4px;">Close</a>',
                    obj.id
                )
            )
        return format_html(' '.join(actions)) if actions else '-'
    quick_actions.short_description = 'Actions'
    
    def has_add_permission(self, request):
        """Quotes are created via API, not admin."""
        return False
    
    def has_view_permission(self, request, obj=None):
        """Allow viewing quotes."""
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """Allow changing quotes."""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting quotes."""
        return request.user.is_staff
    
    def has_module_permission(self, request):
        """Allow the Quote model to appear in admin index."""
        return request.user.is_staff
    
    actions = ['mark_reviewed', 'mark_responded', 'mark_closed', 'export_quotes']
    
    def mark_reviewed(self, request, queryset):
        """Mark selected quotes as reviewed."""
        count = queryset.update(status='reviewed')
        from django.contrib import messages
        messages.success(request, f'✓ {count} quote(s) marked as reviewed.')
    mark_reviewed.short_description = "✓ Mark as Reviewed"
    
    def mark_responded(self, request, queryset):
        """Mark selected quotes as responded."""
        count = queryset.update(status='responded')
        from django.contrib import messages
        messages.success(request, f'✓ {count} quote(s) marked as responded.')
    mark_responded.short_description = "✓ Mark as Responded"
    
    def mark_closed(self, request, queryset):
        """Mark selected quotes as closed."""
        count = queryset.update(status='closed')
        from django.contrib import messages
        messages.success(request, f'✓ {count} quote(s) marked as closed.')
    mark_closed.short_description = "✓ Mark as Closed"
    
    def export_quotes(self, request, queryset):
        """Export selected quotes to CSV."""
        import csv
        from django.http import HttpResponse
        from django.contrib import messages
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="roschi_quotes.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Email', 'Phone', 
            'Message', 'Status', 'Admin Notes', 'Created At', 'Updated At'
        ])
        
        for quote in queryset:
            writer.writerow([
                quote.id,
                quote.first_name,
                quote.last_name,
                quote.email,
                quote.phone,
                quote.message,
                quote.get_status_display(),
                quote.admin_notes,
                quote.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                quote.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        messages.success(request, f'✓ Exported {queryset.count()} quote(s) to CSV.')
        return response
    export_quotes.short_description = "📥 Export Selected Quotes to CSV"


# Register with business admin sites
roschi_admin_site.register(RestaurantSettings, RoschiBusinessSettingsAdmin)
roschi_admin_site.register(Quote, QuoteAdmin)

chopsticks_admin_site.register(RestaurantSettings, ChopsticksBusinessSettingsAdmin)
main_admin_site.register(RestaurantSettings, RestaurantSettingsAdmin)
