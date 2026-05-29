from django.db import models
from django.conf import settings
from django.utils import timezone


class PromoCode(models.Model):
    """Promotional code model."""
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    # Multi-tenant support
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='promo_codes',
        help_text="Business this promo code belongs to",
        null=True,
        blank=True,  # Allow null for existing data migration
    )
    
    code = models.CharField(max_length=20)
    description = models.TextField()
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(
        default=0,
        help_text='Maximum uses per customer (0 for unlimited per customer). Not a global cap.',
    )
    current_usage = models.PositiveIntegerField(
        default=0,
        help_text='Total redemptions across all customers (informational only).',
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['restaurant_settings', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.description[:50]}"
    
    @property
    def is_valid(self):
        """Check if promo code is currently valid."""
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from > now:
            return False
        
        if self.valid_until and self.valid_until < now:
            return False
        
        return True
    
    def get_customer_usage_count(self, user=None, guest_email=None):
        """Count how many times a customer has redeemed this promo."""
        if user and getattr(user, 'is_authenticated', False):
            return PromoCodeUsage.objects.filter(promo_code=self, user=user).count()
        if guest_email:
            email = guest_email.strip().lower()
            if email:
                return PromoCodeUsage.objects.filter(
                    promo_code=self,
                    guest_email__iexact=email,
                ).count()
        return 0
    
    def is_valid_for_customer(self, user=None, guest_email=None):
        """Check per-customer usage limits (usage_limit=0 means unlimited per customer)."""
        if not self.is_valid:
            return False

        usage_count = self.get_customer_usage_count(user=user, guest_email=guest_email)
        if self.usage_limit > 0 and usage_count >= self.usage_limit:
            return False

        return True
    
    def customer_usage_limit_reached(self, user=None, guest_email=None):
        """True when this customer has hit their personal usage cap."""
        if self.usage_limit <= 0:
            return False
        return self.get_customer_usage_count(user=user, guest_email=guest_email) >= self.usage_limit

    def is_valid_for_user(self, user):
        """Backward-compatible alias for authenticated user checks."""
        return self.is_valid_for_customer(user=user)
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order amount."""
        if order_amount < self.minimum_order_amount:
            return 0
        
        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
        else:  # fixed amount
            discount = self.discount_value
        
        # Apply maximum discount limit if set
        if self.maximum_discount:
            discount = min(discount, self.maximum_discount)
        
        # Ensure discount doesn't exceed order amount
        discount = min(discount, order_amount)
        
        return discount


class PromoCodeUsage(models.Model):
    """Track promo code usage by users."""
    
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_code_usages',
        null=True,
        blank=True,
    )
    guest_email = models.EmailField(blank=True, default='')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='promo_code_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['promo_code', 'order']
    
    def __str__(self):
        customer = self.user.email if self.user else (self.guest_email or 'Guest')
        return f"{self.promo_code.code} used by {customer} on {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Increment usage count on promo code
        if not self.pk:  # Only on creation
            self.promo_code.current_usage += 1
            self.promo_code.save()
        
        super().save(*args, **kwargs)
