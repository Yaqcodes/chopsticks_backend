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
