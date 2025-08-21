from django.db import models
from django.conf import settings


class Address(models.Model):
    """User address model."""
    
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Nigeria')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='home')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.address[:50]}..."
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        """Return complete formatted address."""
        postal_part = f" {self.postal_code}" if self.postal_code else ""
        return f"{self.address}, {self.city}, {self.state}{postal_part}, {self.country}"
    
    @property
    def coordinates(self):
        """Return coordinates as tuple if available."""
        if self.latitude and self.longitude:
            return (float(self.latitude), float(self.longitude))
        return None
