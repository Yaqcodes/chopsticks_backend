from django.db import models
from django.conf import settings
from django.utils import timezone


class PromoCode(models.Model):
    """Promotional code model."""
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=0, help_text='0 for unlimited')
    current_usage = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
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
        
        if self.usage_limit > 0 and self.current_usage >= self.usage_limit:
            return False
        
        return True
    
    def is_valid_for_user(self, user):
        """Check if promo code is valid for a specific user."""
        if not self.is_valid:
            return False
        
        # Check if user has already used this code
        if user.is_authenticated:
            usage_count = PromoCodeUsage.objects.filter(
                promo_code=self,
                user=user
            ).count()
            
            if usage_count > 0:
                return False
        
        return True
    
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_code_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='promo_code_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['promo_code', 'order']
    
    def __str__(self):
        return f"{self.promo_code.code} used by {self.user.email} on {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Increment usage count on promo code
        if not self.pk:  # Only on creation
            self.promo_code.current_usage += 1
            self.promo_code.save()
        
        super().save(*args, **kwargs)
