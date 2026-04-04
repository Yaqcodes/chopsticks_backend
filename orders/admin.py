from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem
from core.admin_sites import roschi_admin_site, chopsticks_admin_site, zmall_admin_site
from core.main_admin_site import main_admin_site


class BusinessAdminMixin:
    """
    Mixin to add permission methods for business admin classes.
    
    Ensures that staff users linked to the business can view and manage models.
    """
    
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


def _order_item_inline_all_readonly():
    return ('menu_item', 'quantity', 'unit_price', 'total_price', 'special_instructions')


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""
    
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']
    fields = ['menu_item', 'quantity', 'unit_price', 'total_price', 'special_instructions']

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return list(self.readonly_fields)
        return list(_order_item_inline_all_readonly())

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    
    list_display = [
        'order_number', 'restaurant_settings', 'get_customer_name', 'delivery_type', 'status', 
        'payment_status', 'total_amount', 'created_at'
    ]
    list_filter = [
        'restaurant_settings', 'status', 'payment_status', 'delivery_type', 'created_at'
    ]
    search_fields = [
        'order_number', 'user__email', 'user__username', 
        'guest_email', 'guest_name'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'order_number', 'subtotal', 'tax_amount', 'total_amount', 
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'restaurant_settings', 'status', 'payment_status', 'created_at')
        }),
        ('Customer Information', {
            'fields': ('guest_email', 'guest_name', 'guest_phone')
        }),
        ('Delivery Details', {
            'fields': ('delivery_address', 'delivery_type', 'special_instructions')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'delivery_fee', 'discount_amount', 'total_amount')
        }),
        ('Payment', {
            'fields': ('paystack_reference', 'paystack_access_code', 'payment_verified_at')
        }),
        ('Timing', {
            'fields': ('estimated_delivery_time', 'actual_delivery_time')
        }),
    )
    
    inlines = [OrderItemInline]
    
    def get_customer_name(self, obj):
        """Display customer name."""
        return obj.get_customer_name()
    get_customer_name.short_description = 'Customer'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related('user', 'restaurant_settings')
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_delivered']
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed."""
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark selected orders as confirmed"
    
    def mark_as_preparing(self, request, queryset):
        """Mark selected orders as preparing."""
        updated = queryset.update(status='preparing')
        self.message_user(request, f'{updated} orders marked as preparing.')
    mark_as_preparing.short_description = "Mark selected orders as preparing"
    
    def mark_as_ready(self, request, queryset):
        """Mark selected orders as ready."""
        updated = queryset.update(status='ready')
        self.message_user(request, f'{updated} orders marked as ready.')
    mark_as_ready.short_description = "Mark selected orders as ready"
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected orders as delivered."""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as delivered"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for OrderItem model."""
    
    list_display = ['order', 'menu_item', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['order__order_number', 'menu_item__name']
    ordering = ['-order__created_at']
    readonly_fields = ['total_price']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Allow staff to view order lines; only superusers may mutate (see change/add/delete)."""
        return request.user.is_active and request.user.is_staff

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return list(self.readonly_fields)
        return [f.name for f in self.model._meta.fields]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order', 'menu_item')


# Roschi Water Admin Classes
class RoschiOrderItemInline(TabularInline):
    """Products in this order - what the customer ordered."""
    
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']
    fields = ['menu_item', 'quantity', 'unit_price', 'total_price']
    verbose_name = "Product"
    verbose_name_plural = "Products in This Order"

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return list(self.readonly_fields)
        return ['menu_item', 'quantity', 'unit_price', 'total_price']

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Filter order items to only show items for this business."""
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(order__restaurant_settings=business_settings)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class RoschiOrderAdmin(BusinessAdminMixin, ModelAdmin):
    """Orders - View and manage customer orders."""
    
    list_display = [
        'order_number', 'get_customer_name', 'get_customer_phone', 'total_amount_display', 
        'order_status_display', 'payment_status_display', 'order_date'
    ]
    list_filter = [
        'status', 'payment_status', 'created_at'
    ]
    search_fields = [
        'order_number', 'guest_email', 'guest_name', 'guest_phone', 'delivery_address'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'order_number', 'subtotal', 'tax_amount', 'total_amount', 
        'created_at', 'updated_at', 'paystack_reference'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'payment_status', 'created_at'),
            'description': 'Order number and current status'
        }),
        ('Customer Details', {
            'fields': ('guest_name', 'guest_email', 'guest_phone'),
            'description': 'Contact information for the customer'
        }),
        ('Where to Deliver', {
            'fields': ('delivery_address',),
            'description': 'The address where the order should be delivered'
        }),
        ('Order Total', {
            'fields': ('subtotal', 'tax_amount', 'delivery_fee', 'total_amount'),
            'description': 'Breakdown of what the customer paid'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Add user-friendly help text to form fields."""
        form = super().get_form(request, obj, **kwargs)
        
        # Update field labels
        if 'status' in form.base_fields:
            form.base_fields['status'].label = 'Order Status'
            form.base_fields['status'].help_text = 'Current stage of this order (Pending → Confirmed → Preparing → Ready → Delivered)'
        
        if 'payment_status' in form.base_fields:
            form.base_fields['payment_status'].label = 'Payment Status'
            form.base_fields['payment_status'].help_text = 'Whether the customer has paid for this order'
        
        if 'guest_name' in form.base_fields:
            form.base_fields['guest_name'].label = 'Customer Name'
        
        if 'guest_email' in form.base_fields:
            form.base_fields['guest_email'].label = 'Customer Email'
        
        if 'guest_phone' in form.base_fields:
            form.base_fields['guest_phone'].label = 'Customer Phone Number'
        
        if 'delivery_address' in form.base_fields:
            form.base_fields['delivery_address'].label = 'Delivery Address'
            form.base_fields['delivery_address'].help_text = 'Full address where the order should be delivered'
        
        return form
    
    inlines = [RoschiOrderItemInline]
    
    def get_customer_name(self, obj):
        """Customer's full name."""
        return obj.get_customer_name() or 'Guest Customer'
    get_customer_name.short_description = 'Customer Name'
    
    def get_customer_phone(self, obj):
        """Customer's phone number."""
        return obj.guest_phone or 'Not provided'
    get_customer_phone.short_description = 'Phone Number'
    
    def order_date(self, obj):
        """When the order was placed."""
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
    order_date.short_description = 'Order Date'
    
    def total_amount_display(self, obj):
        """Total amount customer paid."""
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'
    
    def order_status_display(self, obj):
        """Current status of the order."""
        status_map = {
            'pending': ('⏳', 'Pending', '#f59e0b'),
            'confirmed': ('✓', 'Confirmed', '#3b82f6'),
            'preparing': ('👨‍🍳', 'Preparing', '#8b5cf6'),
            'ready': ('📦', 'Ready for Delivery', '#06b6d4'),
            'delivered': ('✓', 'Delivered', '#10b981'),
            'cancelled': ('✗', 'Cancelled', '#ef4444'),
        }
        icon, label, color = status_map.get(obj.status, ('❓', obj.status.title(), '#6b7280'))
        return format_html('<span style="color: {}; font-weight: bold;">{} {}</span>', color, icon, label)
    order_status_display.short_description = 'Order Status'
    
    def payment_status_display(self, obj):
        """Whether payment was successful."""
        if obj.payment_status == 'paid':
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ Paid</span>')
        elif obj.payment_status == 'pending':
            return format_html('<span style="color: #f59e0b; font-weight: bold;">⏳ Payment Pending</span>')
        else:
            return format_html('<span style="color: #ef4444; font-weight: bold;">✗ Payment Failed</span>')
    payment_status_display.short_description = 'Payment Status'
    
    def get_queryset(self, request):
        """Filter to only show orders for this business."""
        qs = super().get_queryset(request).select_related('user', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        """Ensure business settings is set to this business."""
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_delivered']
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed."""
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark selected orders as confirmed"
    
    def mark_as_preparing(self, request, queryset):
        """Mark selected orders as preparing."""
        updated = queryset.update(status='preparing')
        self.message_user(request, f'{updated} orders marked as preparing.')
    mark_as_preparing.short_description = "Mark selected orders as preparing"
    
    def mark_as_ready(self, request, queryset):
        """Mark selected orders as ready."""
        updated = queryset.update(status='ready')
        self.message_user(request, f'{updated} orders marked as ready.')
    mark_as_ready.short_description = "Mark selected orders as ready"
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected orders as delivered."""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as delivered"


class RoschiOrderItemAdmin(BusinessAdminMixin, ModelAdmin):
    """Order Items - Individual products that were ordered."""
    
    list_display = ['order', 'menu_item', 'quantity', 'unit_price_display', 'total_price_display']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['order__order_number', 'menu_item__name']
    ordering = ['-order__created_at']
    readonly_fields = ['total_price']

    def has_add_permission(self, request):
        if not request.user.is_superuser:
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return list(self.readonly_fields)
        return [f.name for f in self.model._meta.fields]
    
    def unit_price_display(self, obj):
        """Price per unit."""
        return f"₦{obj.unit_price:,.2f}"
    unit_price_display.short_description = 'Price Each'
    
    def total_price_display(self, obj):
        """Total for this item (price × quantity)."""
        return f"₦{obj.total_price:,.2f}"
    total_price_display.short_description = 'Item Total'
    
    def get_queryset(self, request):
        """Filter to only show order items for this business."""
        qs = super().get_queryset(request).select_related('order', 'menu_item', 'order__restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(order__restaurant_settings=business_settings)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


# Register with business admin sites
roschi_admin_site.register(Order, RoschiOrderAdmin)
roschi_admin_site.register(OrderItem, RoschiOrderItemAdmin)
chopsticks_admin_site.register(Order, RoschiOrderAdmin)
chopsticks_admin_site.register(OrderItem, RoschiOrderItemAdmin)
zmall_admin_site.register(Order, RoschiOrderAdmin)
zmall_admin_site.register(OrderItem, RoschiOrderItemAdmin)
main_admin_site.register(Order, OrderAdmin)
main_admin_site.register(OrderItem, OrderItemAdmin)
