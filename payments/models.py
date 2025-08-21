from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone


class Payment(models.Model):
    """Payment model to track Paystack transactions."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    # Payment identification
    reference = models.CharField(max_length=100, unique=True, help_text="Paystack transaction reference")
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    
    # Amount and currency
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in Naira")
    amount_kobo = models.IntegerField(help_text="Amount in kobo for Paystack")
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paystack_status = models.CharField(max_length=50, blank=True, help_text="Raw status from Paystack")
    
    # Paystack response data
    access_code = models.CharField(max_length=100, blank=True, help_text="Paystack access code")
    authorization_url = models.URLField(blank=True, help_text="Paystack checkout URL")
    customer_email = models.EmailField(help_text="Customer email for payment")
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional payment metadata")
    
    # Timestamps
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When payment was verified")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reference} - {self.status} - {self.amount} {self.currency}"
    
    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status == 'success'
    
    def verify_payment(self):
        """Verify payment with Paystack API."""
        from .services import PaystackService
        
        try:
            paystack = PaystackService()
            result = paystack.verify_transaction(self.reference)
            
            # Update payment status
            self.paystack_status = result.get('status', '')
            self.verified_at = timezone.now()
            
            if result.get('status') == 'success':
                self.status = 'success'
            else:
                self.status = 'failed'
            
            self.save()
            return result
            
        except Exception as e:
            self.status = 'failed'
            self.save()
            raise e
