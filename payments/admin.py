from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Payment
from django.utils import timezone


@admin.register(Payment)
class PaymentAdmin(UnfoldModelAdmin):
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
        
        paystack = PaystackService()
        verified_count = 0
        
        for payment in queryset:
            try:
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
        return super().get_queryset(request).select_related('order')
