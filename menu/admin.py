from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Category, MenuItem
from core.admin_sites import roschi_admin_site, chopsticks_admin_site
from core.main_admin_site import main_admin_site


class BusinessAdminMixin:
    """
    Mixin to add permission methods for business admin classes.
    
    Ensures that staff users linked to the business can view and manage models.
    """
    
    def has_module_permission(self, request):
        """Check if user can view this app in admin."""
        # Delegate to admin site's permission check
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        # Fallback for default admin site
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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    
    list_display = ['name', 'is_active', 'sort_order', 'menu_items_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    
    def menu_items_count(self, obj):
        """Display count of menu items in category."""
        return obj.menu_items.count()
    menu_items_count.short_description = 'Menu Items'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for MenuItem model."""
    
    list_display = ['name', 'category', 'size', 'sku', 'restaurant_settings', 'price', 'is_available', 'is_featured', 'sort_order']
    list_filter = ['restaurant_settings', 'category', 'is_available', 'is_featured', 'badges', 'created_at']
    search_fields = ['name', 'description', 'size', 'category__name']
    ordering = ['category', 'sort_order', 'name']
    list_editable = ['is_available', 'is_featured', 'sort_order']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'size', 'sku', 'category', 'restaurant_settings', 'price', 'image')
        }),
        ('Status & Display', {
            'fields': ('is_available', 'is_featured', 'sort_order', 'preparation_time')
        }),
        ('Additional Information', {
            'fields': ('badges', 'allergens', 'nutritional_info'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('category', 'restaurant_settings')


# Roschi Water Admin Classes
class RoschiCategoryAdmin(BusinessAdminMixin, ModelAdmin):
    """Product categories - Organize your products into groups like 'Bottled Water' or 'Sachet Water'."""
    
    list_display = ['name', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    list_editable = ['is_active']
    
    def product_count(self, obj):
        """How many products are in this category."""
        business_settings = self._get_business_settings()
        if business_settings:
            return obj.menu_items.filter(restaurant_settings=business_settings).count()
        return 0
    product_count.short_description = 'Number of Products'
    
    def get_queryset(self, request):
        """Show only categories that have products for this business."""
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(menu_items__restaurant_settings=business_settings).distinct()
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class RoschiMenuItemAdmin(BusinessAdminMixin, ModelAdmin):
    """Products - Manage your water products that customers can order."""
    
    list_display = ['name', 'category', 'size', 'sku', 'price_display', 'is_available', 'stock_status']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description', 'size', 'category__name']
    ordering = ['category', 'name']
    list_editable = ['is_available', 'sku']
    
    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'description', 'category', 'size', 'price', 'image'),
            'description': 'What customers will see when browsing your products'
        }),
        ('Stock Management', {
            'fields': ('sku', 'is_available'),
            'description': 'How many units you have in stock and whether customers can order this product'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Add user-friendly help text to form fields."""
        form = super().get_form(request, obj, **kwargs)
        
        # Update field labels and help text
        if 'name' in form.base_fields:
            form.base_fields['name'].label = 'Product Name'
            form.base_fields['name'].help_text = 'The name customers will see (e.g., "ROSCHI Bottled Water")'
        
        if 'description' in form.base_fields:
            form.base_fields['description'].label = 'Product Description'
            form.base_fields['description'].help_text = 'Describe your product to customers'
        
        if 'size' in form.base_fields:
            form.base_fields['size'].label = 'Size or Pack'
            form.base_fields['size'].help_text = 'Product size or pack information (e.g., "24-pack 35cl", "Pure Water")'
        
        if 'price' in form.base_fields:
            form.base_fields['price'].label = 'Price (₦)'
            form.base_fields['price'].help_text = 'How much customers pay for this product in Naira'
        
        if 'category' in form.base_fields:
            form.base_fields['category'].label = 'Product Category'
            form.base_fields['category'].help_text = 'Which category this product belongs to (e.g., Bottled Water, Sachet Water)'
        
        if 'image' in form.base_fields:
            form.base_fields['image'].label = 'Product Image'
            form.base_fields['image'].help_text = 'Upload a photo of your product. Customers will see this image.'
        
        if 'sku' in form.base_fields:
            form.base_fields['sku'].label = 'Stock Quantity'
            form.base_fields['sku'].help_text = 'How many units of this product you currently have in stock'
        
        if 'is_available' in form.base_fields:
            form.base_fields['is_available'].label = 'Available for Order'
            form.base_fields['is_available'].help_text = 'Turn this off to temporarily hide the product from customers'
        
        return form
    
    def get_queryset(self, request):
        """Show only products for this business."""
        qs = super().get_queryset(request).select_related('category', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    def price_display(self, obj):
        """Show price in Naira."""
        return f"₦{obj.price:,.2f}"
    price_display.short_description = 'Price'
    
    def stock_status(self, obj):
        """Show if product is in stock, low stock, or out of stock."""
        if obj.sku == 0:
            return format_html('<span style="color: #ef4444; font-weight: bold;">⚠️ Out of Stock</span>')
        elif obj.sku < 10:
            return format_html('<span style="color: #f59e0b; font-weight: bold;">⚠️ Low Stock - Only {} left!</span>', obj.sku)
        else:
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ In Stock ({} available)</span>', obj.sku)
    stock_status.short_description = 'Availability'
    
    def save_model(self, request, obj, form, change):
        """Automatically link product to this business."""
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)


# Register with business admin sites
roschi_admin_site.register(Category, RoschiCategoryAdmin)
roschi_admin_site.register(MenuItem, RoschiMenuItemAdmin)
chopsticks_admin_site.register(Category, RoschiCategoryAdmin)
chopsticks_admin_site.register(MenuItem, RoschiMenuItemAdmin)
main_admin_site.register(Category, CategoryAdmin)
main_admin_site.register(MenuItem, MenuItemAdmin)
