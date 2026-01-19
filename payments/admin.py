from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Payment
from core.admin_sites import roschi_admin_site, chopsticks_admin_site
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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    
    list_display = [
        'reference', 'order', 'amount', 'currency', 'status', 
        'customer_email', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at', 'verified_at']
    search_fields = ['reference', 'customer_email', 'order__order_number']
    ordering = ['-created_at']
    readonly_fields = [
        'reference', 'created_at', 'updated_at', 'verified_at', 
        'authorization_url', 'access_code'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('reference', 'order', 'amount', 'amount_kobo', 'currency')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'paystack_status', 'verified_at')
        }),
        ('Paystack Data', {
            'fields': ('access_code', 'authorization_url', 'customer_email'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_payments', 'mark_as_success', 'mark_as_failed']
    
    def verify_payments(self, request, queryset):
        """Verify selected payments with Paystack."""
        from .services import PaystackService
        
        verified_count = 0
        
        for payment in queryset:
            try:
                restaurant_settings = payment.order.restaurant_settings
                paystack = PaystackService(secret_key=restaurant_settings.paystack_secret_key)
                result = paystack.verify_transaction(payment.reference)
                payment.paystack_status = result.get('status', '')
                payment.verified_at = timezone.now()
                
                if result.get('status') == 'success':
                    payment.status = 'success'
                    verified_count += 1
                else:
                    payment.status = 'failed'
                
                payment.save()
                
            except Exception as e:
                self.message_user(request, f"Error verifying {payment.reference}: {str(e)}", level='ERROR')
        
        self.message_user(request, f'{verified_count} payments verified successfully.')
    verify_payments.short_description = "Verify payments with Paystack"
    
    def mark_as_success(self, request, queryset):
        """Mark selected payments as successful."""
        count = queryset.update(status='success')
        self.message_user(request, f'{count} payments marked as successful.')
    mark_as_success.short_description = "Mark as successful"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed."""
        count = queryset.update(status='failed')
        self.message_user(request, f'{count} payments marked as failed.')
    mark_as_failed.short_description = "Mark as failed"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order', 'order__restaurant_settings')


# Roschi Water Admin Class
class RoschiPaymentAdmin(BusinessAdminMixin, ModelAdmin):
    """Payments - Track all customer payments and transactions."""
    
    list_display = [
        'payment_reference', 'order', 'amount_display', 'status_display', 
        'customer_email', 'payment_date'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['reference', 'customer_email', 'order__order_number']
    ordering = ['-created_at']
    readonly_fields = [
        'reference', 'order', 'amount', 'currency', 'status', 
        'created_at', 'verified_at'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('reference', 'order', 'amount', 'currency', 'status'),
            'description': 'Details about this payment transaction'
        }),
        ('Customer', {
            'fields': ('customer_email',),
            'description': 'Email address of the customer who made this payment'
        }),
        ('Payment Timeline', {
            'fields': ('created_at', 'verified_at'),
            'description': 'When the payment was made and when it was confirmed'
        }),
    )
    
    def payment_reference(self, obj):
        """Payment reference number."""
        return obj.reference
    payment_reference.short_description = 'Payment Reference'
    
    def payment_date(self, obj):
        """When the payment was made."""
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
    payment_date.short_description = 'Payment Date'
    
    def amount_display(self, obj):
        """How much the customer paid."""
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount Paid'
    
    def status_display(self, obj):
        """Whether the payment was successful."""
        if obj.status == 'success':
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ Payment Successful</span>')
        elif obj.status == 'pending':
            return format_html('<span style="color: #f59e0b; font-weight: bold;">⏳ Waiting for Payment</span>')
        else:
            return format_html('<span style="color: #ef4444; font-weight: bold;">✗ Payment Failed</span>')
    status_display.short_description = 'Payment Status'
    
    def get_queryset(self, request):
        """Filter to only show payments for this business."""
        qs = super().get_queryset(request).select_related('order', 'order__restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(order__restaurant_settings=business_settings)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    actions = ['verify_payments', 'mark_as_success', 'mark_as_failed']
    
    def verify_payments(self, request, queryset):
        """Check with Paystack to confirm these payments were successful."""
        from .services import PaystackService
        
        verified_count = 0
        
        for payment in queryset:
            try:
                restaurant_settings = payment.order.restaurant_settings
                if not restaurant_settings.paystack_secret_key:
                    self.message_user(
                        request, 
                        f"Payment settings not configured. Please check Business Settings.", 
                        level='ERROR'
                    )
                    continue
                    
                paystack = PaystackService(secret_key=restaurant_settings.paystack_secret_key)
                result = paystack.verify_transaction(payment.reference)
                payment.paystack_status = result.get('status', '')
                payment.verified_at = timezone.now()
                
                if result.get('status') == 'success':
                    payment.status = 'success'
                    verified_count += 1
                else:
                    payment.status = 'failed'
                
                payment.save()
                
            except Exception as e:
                self.message_user(request, f"Could not verify payment {payment.reference}. Please try again later.", level='ERROR')
        
        self.message_user(request, f'✓ {verified_count} payment(s) verified successfully.')
    verify_payments.short_description = "✓ Verify Payments"
    
    def mark_as_success(self, request, queryset):
        """Manually mark these payments as successful (use if you confirmed payment another way)."""
        count = queryset.update(status='success')
        self.message_user(request, f'✓ {count} payment(s) marked as successful.')
    mark_as_success.short_description = "✓ Mark as Paid"
    
    def mark_as_failed(self, request, queryset):
        """Mark these payments as failed (customer payment did not go through)."""
        count = queryset.update(status='failed')
        self.message_user(request, f'✗ {count} payment(s) marked as failed.')
    mark_as_failed.short_description = "✗ Mark as Failed"


# Register with business admin sites
roschi_admin_site.register(Payment, RoschiPaymentAdmin)
chopsticks_admin_site.register(Payment, RoschiPaymentAdmin)
main_admin_site.register(Payment, PaymentAdmin)
