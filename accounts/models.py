from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import random
import string


def generate_referral_code():
    """Generate a unique 8-character referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class User(AbstractUser):
    """Custom User model with additional fields for the restaurant app."""
    
    # Additional fields
    phone = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    referral_code = models.CharField(max_length=8, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='referrals')
    
    # Business linkage for multi-tenant admin access
    businesses = models.ManyToManyField(
        'core.RestaurantSettings',
        related_name='staff_users',
        blank=True,
        help_text="Businesses this user can manage. Superusers can access all businesses."
    )
    
    # Override email field to be unique
    email = models.EmailField(unique=True)
    
    # Override username field to be optional
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    
    # Required fields for creating a user
    REQUIRED_FIELDS = ['email']
    
    def __str__(self):
        return self.email or self.username
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            # Generate a unique referral code
            while True:
                code = generate_referral_code()
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def has_business_access(self, restaurant_settings):
        """
        Check if user has access to a specific business.
        
        Args:
            restaurant_settings: RestaurantSettings instance or ID
            
        Returns:
            bool: True if user is superuser or linked to the business
        """
        if self.is_superuser:
            return True
        
        if isinstance(restaurant_settings, int):
            return self.businesses.filter(id=restaurant_settings).exists()
        
        return self.businesses.filter(id=restaurant_settings.id).exists()
    
    def get_accessible_businesses(self):
        """
        Get all businesses this user can access.
        
        Returns:
            QuerySet: RestaurantSettings queryset
        """
        if self.is_superuser:
            from core.models import RestaurantSettings
            return RestaurantSettings.objects.all()
        return self.businesses.all()


class SocialAccount(models.Model):
    """Model for storing social authentication accounts."""
    
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('apple', 'Apple'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['provider', 'provider_user_id']
    
    def __str__(self):
        return f"{self.user.email} - {self.provider}"
