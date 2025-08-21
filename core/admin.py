from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import RestaurantSettings
from django.shortcuts import render


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(UnfoldModelAdmin):
    """Admin interface for RestaurantSettings model."""
    
    list_display = ['name', 'restaurant_coordinates', 'delivery_fee_base', 'delivery_fee_per_km', 'delivery_radius', 'is_open', 'delivery_fee_info', 'current_delivery_fee', 'updated_at']
    list_editable = ['delivery_fee_base', 'delivery_fee_per_km', 'delivery_radius', 'is_open']
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['name', 'address', 'phone', 'email']
    list_filter = ['is_open', 'maintenance_mode', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    save_on_top = True
    save_as_continue = False
    
    # Customize field labels and help text
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'address', 'phone', 'email', 'website')
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
                'delivery_fee_base',
                'delivery_fee_per_km',
                'pickup_delivery_fee',
                'vat_rate'
            ),
            'description': 'Configure delivery fees, radius, and thresholds. Delivery fee = Base + (Distance × Per KM)'
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
    
    actions = ['reset_delivery_fees', 'enable_free_delivery', 'disable_free_delivery', 'set_nigerian_city_coordinates']
    
    def has_add_permission(self, request):
        """Only allow one settings instance."""
        return not RestaurantSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of restaurant settings."""
        return False
    
    def get_form(self, request, obj=None, **kwargs):
        """Custom form with enhanced help text for delivery fees."""
        form = super().get_form(request, obj, **kwargs)
        
        # Add helpful text for delivery fee fields
        if form.base_fields.get('delivery_fee_base'):
            form.base_fields['delivery_fee_base'].help_text = (
                'Base delivery fee in Naira (₦). This is the minimum delivery charge.'
            )
        
        if form.base_fields.get('delivery_fee_per_km'):
            form.base_fields['delivery_fee_per_km'].help_text = (
                'Additional fee per kilometer in Naira (₦). Total delivery fee = Base + (Distance × Per KM)'
            )
        
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
    
    def delivery_fee_info(self, obj):
        """Display delivery fee calculation information."""
        if obj.delivery_fee_base and obj.delivery_fee_per_km:
            return f"Base: ₦{obj.delivery_fee_base} + ₦{obj.delivery_fee_per_km}/km"
        elif obj.delivery_fee_base:
            return f"Fixed: ₦{obj.delivery_fee_base}"
        else:
            return "Not configured"
    delivery_fee_info.short_description = "Delivery Fee Structure"
    
    def reset_delivery_fees(self, request, queryset):
        """Reset delivery fees to default values."""
        from django.conf import settings
        count = 0
        for settings_obj in queryset:
            settings_obj.delivery_fee_base = getattr(settings, 'DEFAULT_DELIVERY_FEE_BASE', 2000.00)
            settings_obj.delivery_fee_per_km = getattr(settings, 'DEFAULT_DELIVERY_FEE_PER_KM', 150.00)
            settings_obj.save()
            count += 1
        
        self.message_user(request, f'Successfully reset delivery fees for {count} restaurant settings.')
    reset_delivery_fees.short_description = "Reset delivery fees to defaults"
    
    def enable_free_delivery(self, request, queryset):
        """Enable free delivery by setting delivery fees to 0."""
        count = 0
        for settings_obj in queryset:
            settings_obj.delivery_fee_base = 0.00
            settings_obj.delivery_fee_per_km = 0.00
            settings_obj.save()
            count += 1
        
        self.message_user(request, f'Successfully enabled free delivery for {count} restaurant settings.')
    enable_free_delivery.short_description = "Enable free delivery"
    
    def disable_free_delivery(self, request, queryset):
        """Disable free delivery by setting default delivery fees."""
        from django.conf import settings
        count = 0
        for settings_obj in queryset:
            settings_obj.delivery_fee_base = getattr(settings, 'DEFAULT_DELIVERY_FEE_BASE', 2000.00)
            settings_obj.delivery_fee_per_km = getattr(settings, 'DEFAULT_DELIVERY_FEE_PER_KM', 150.00)
            settings_obj.save()
            count += 1
        
        self.message_user(request, f'Successfully disabled free delivery for {count} restaurant settings.')
    disable_free_delivery.short_description = "Disable free delivery"
    
    def current_delivery_fee(self, obj):
        """Display current delivery fee calculation example."""
        if obj.delivery_fee_base and obj.delivery_fee_per_km:
            example_5km = obj.delivery_fee_base + (5 * obj.delivery_fee_per_km)
            example_10km = obj.delivery_fee_base + (10 * obj.delivery_fee_per_km)
            return f"5km: ₦{example_5km:.2f}, 10km: ₦{example_10km:.2f}"
        elif obj.delivery_fee_base:
            return f"Fixed: ₦{obj.delivery_fee_base:.2f}"
        else:
            return "Free delivery"
    current_delivery_fee.short_description = "Example Delivery Fees"
    
    def set_nigerian_city_coordinates(self, request, queryset):
        """Set coordinates for common Nigerian cities."""
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
    set_nigerian_city_coordinates.short_description = "Set coordinates for Nigerian city"
