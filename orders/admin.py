from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""
    
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']
    fields = ['menu_item', 'quantity', 'unit_price', 'total_price', 'special_instructions']


@admin.register(Order)
class OrderAdmin(UnfoldModelAdmin):
    """Admin interface for Order model."""
    
    list_display = [
        'order_number', 'get_customer_name', 'delivery_type', 'status', 
        'payment_status', 'total_amount', 'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'delivery_type', 'created_at'
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
            'fields': ('order_number', 'user', 'status', 'payment_status', 'created_at')
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
        return super().get_queryset(request).select_related('user')
    
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
class OrderItemAdmin(UnfoldModelAdmin):
    """Admin interface for OrderItem model."""
    
    list_display = ['order', 'menu_item', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['order__order_number', 'menu_item__name']
    ordering = ['-order__created_at']
    readonly_fields = ['total_price']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order', 'menu_item')
