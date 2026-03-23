from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


def get_default_expiration_date():
    """Get default expiration date (30 days from now)."""
    return timezone.now() + timedelta(days=30)


class UserPoints(models.Model):
    """User points balance model - business-scoped."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points')
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='user_points',
        help_text="Business this points balance belongs to"
    )
    balance = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_spent = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'User Points'
        unique_together = [('user', 'restaurant_settings')]
        indexes = [
            models.Index(fields=['user', 'restaurant_settings']),
            models.Index(fields=['restaurant_settings', '-balance']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.restaurant_settings.name} - {self.balance} points"
    
    def add_points(self, amount, reason=''):
        """Add points to user balance."""
        self.balance += amount
        self.total_earned += amount
        self.save()
        
        # Create transaction record with business context
        PointsTransaction.objects.create(
            user=self.user,
            restaurant_settings=self.restaurant_settings,
            amount=amount,
            transaction_type='earned',
            reason=reason,
            balance_after=self.balance
        )
    
    def spend_points(self, amount, reason=''):
        """Spend points from user balance."""
        if self.balance < amount:
            raise ValueError("Insufficient points balance")
        
        self.balance -= amount
        self.total_spent += amount
        self.save()
        
        # Create transaction record with business context
        PointsTransaction.objects.create(
            user=self.user,
            restaurant_settings=self.restaurant_settings,
            amount=amount,
            transaction_type='spent',
            reason=reason,
            balance_after=self.balance
        )


class PointsTransaction(models.Model):
    """Points transaction history model - business-scoped."""
    
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('spent', 'Spent'),
        ('expired', 'Expired'),
        ('bonus', 'Bonus'),
        ('referral', 'Referral Bonus'),
        ('birthday', 'Birthday Bonus'),
        ('first_order', 'First Order Bonus'),
        ('physical_visit', 'Physical Visit'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='points_transactions')
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='points_transactions',
        help_text="Business this transaction belongs to"
    )
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    reason = models.CharField(max_length=200, blank=True)
    balance_after = models.PositiveIntegerField()
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'restaurant_settings', '-created_at']),
            models.Index(fields=['restaurant_settings', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.restaurant_settings.name} - {self.amount} points ({self.transaction_type})"


class Reward(models.Model):
    """Available rewards model."""
    
    REWARD_TYPES = [
        ('discount', 'Discount'),
        ('free_item', 'Free Item'),
        ('free_delivery', 'Free Delivery'),
        ('cashback', 'Cashback'),
    ]
    
    # Multi-tenant support
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='rewards',
        help_text="Business this reward belongs to",
        null=True,
        blank=True,  # Allow null for existing data migration
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPES)
    points_required = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_item = models.ForeignKey('menu.MenuItem', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    max_redemptions = models.PositiveIntegerField(default=0, help_text='0 for unlimited')
    current_redemptions = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['points_required']
    
    def __str__(self):
        return f"{self.name} - {self.points_required} points"
    
    @property
    def is_available(self):
        """Check if reward is available for redemption."""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from > now:
            return False
        
        if self.valid_until and self.valid_until < now:
            return False
        
        if self.max_redemptions > 0 and self.current_redemptions >= self.max_redemptions:
            return False
        
        return True
    
    def can_be_redeemed_by(self, user, restaurant_settings):
        """Check if user can redeem this reward for a specific business."""
        try:
            user_points = UserPoints.objects.get(user=user, restaurant_settings=restaurant_settings)
            return user_points.balance >= self.points_required
        except UserPoints.DoesNotExist:
            return False


class UserReward(models.Model):
    """User redeemed rewards model - business-scoped."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='redeemed_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='user_rewards',
        help_text="Business this reward redemption belongs to"
    )
    points_spent = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    redeemed_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=get_default_expiration_date)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-redeemed_at']
        indexes = [
            models.Index(fields=['user', 'restaurant_settings', '-redeemed_at']),
            models.Index(fields=['restaurant_settings', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.restaurant_settings.name} - {self.reward.name}"
    
    @property
    def is_expired(self):
        """Check if reward is expired."""
        from django.utils import timezone
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False
    
    def use_reward(self, order=None):
        """Mark reward as used."""
        from django.utils import timezone
        self.status = 'used'
        self.used_at = timezone.now()
        self.order = order
        self.save()
    
    def check_and_update_expired_status(self):
        """Check if reward is expired and update status if needed."""
        if self.is_expired and self.status == 'active':
            self.status = 'expired'
            self.save()
            return True
        return False


class LoyaltyCard(models.Model):
    """Loyalty card model for QR code scanning - business-scoped."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty_cards', null=True, blank=True)
    restaurant_settings = models.ForeignKey(
        'core.RestaurantSettings',
        on_delete=models.CASCADE,
        related_name='loyalty_cards',
        help_text="Business this loyalty card belongs to"
    )
    qr_code = models.CharField(max_length=255, help_text="Customer ID number or LOYALTY- code")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_scan = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Loyalty Cards'
        unique_together = [('restaurant_settings', 'qr_code')]
        indexes = [
            models.Index(fields=['restaurant_settings', 'qr_code']),
            models.Index(fields=['user', 'restaurant_settings']),
        ]
    
    def __str__(self):
        user_info = self.user.email if self.user else "Unassigned"
        return f"Loyalty Card - {user_info} - {self.restaurant_settings.name} (ID: {self.qr_code})"
    
    def generate_qr_code(self):
        """Generate a unique QR code for this loyalty card."""
        import uuid
        if not self.qr_code:
            # Generate a new LOYALTY- format code for new cards
            self.qr_code = f"LOYALTY-{uuid.uuid4().hex[:12].upper()}"
        return self.qr_code
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def scan_card(self):
        """Mark card as scanned and update last scan time."""
        from django.utils import timezone
        self.last_scan = timezone.now()
        self.save()
    
    def link_to_user(self, user):
        """Link this card to a user and activate it."""
        self.user = user
        self.is_active = True
        self.save()
    
    def unlink_user(self):
        """Unlink user from card and deactivate it."""
        self.user = None
        self.is_active = False
        self.save()
    
    def activate_card(self):
        """Activate card if it has a user assigned."""
        if self.user:
            self.is_active = True
            self.save()
            return True
        return False
    
    def deactivate_card(self):
        """Deactivate card."""
        self.is_active = False
        self.save()
    
    @property
    def google_script_url(self):
        """Generate the Google Apps Script URL for this card."""
        if self.qr_code.isdigit():
            return f"https://script.google.com/macros/s/AKfycbyu11a9M5g4oLUs_sGF9e8SJM1KLb_8PZajkWkmFd2tO9YdQvhMpCjrfp959uMjzsdJ/exec?customerID={self.qr_code}"
        return None
    
    @property
    def status_display(self):
        """Get human-readable status."""
        if not self.user:
            return "Unassigned"
        elif self.is_active:
            return "Active"
        else:
            return "Inactive"
