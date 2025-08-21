from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class TimeStampedModel(models.Model):
    """Abstract base model with timestamp fields."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class RestaurantSettings(models.Model):
    """Restaurant settings and configuration."""
    
    # Basic Information
    name = models.CharField(max_length=200, default="Chopsticks and Bowls")
    description = models.TextField(blank=True, default="Authentic Korean Cuisine in Abuja")
    tagline = models.CharField(max_length=200, blank=True, default="Authentic Korean Cuisine in Abuja")
    
    # Contact Information
    address = models.TextField(default="Abuja, Nigeria")
    phone = models.CharField(max_length=20, default="+234")
    email = models.EmailField(default="info@chopsticksandbowls.com")
    website = models.URLField(blank=True, default="https://chopsticksandbowls.com")
    
    # Restaurant Coordinates (for distance calculations)
    restaurant_latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        default=9.0820, 
        help_text="Restaurant latitude coordinate",
        validators=[
            MinValueValidator(Decimal('4.0'), message="Latitude must be at least 4.0 (Southern Nigeria)"),
            MaxValueValidator(Decimal('14.0'), message="Latitude must be at most 14.0 (Northern Nigeria)")
        ]
    )
    restaurant_longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        default=7.3986, 
        help_text="Restaurant longitude coordinate",
        validators=[
            MinValueValidator(Decimal('2.0'), message="Longitude must be at least 2.0 (Western Nigeria)"),
            MaxValueValidator(Decimal('15.0'), message="Longitude must be at most 15.0 (Eastern Nigeria)")
        ]
    )
    
    # Operating Hours
    opening_hours = models.JSONField(default=dict)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True, default="https://instagram.com/chop.sticksandbowls")
    twitter_url = models.URLField(blank=True)
    
    # Branding
    logo = models.ImageField(upload_to='restaurant/', blank=True, null=True)
    favicon = models.ImageField(upload_to='restaurant/', blank=True, null=True)
    
    # Delivery Settings
    delivery_radius = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    minimum_order = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    free_delivery_threshold = models.DecimalField(max_digits=8, decimal_places=2, default=50.00)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=3, default=settings.DEFAULT_TAX_RATE, help_text="VAT rate as decimal (e.g., 0.075 for 7.5%)")
    pickup_delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Fee for pickup orders")
    delivery_fee_base = models.DecimalField(max_digits=8, decimal_places=2, default=settings.DEFAULT_DELIVERY_FEE_BASE, help_text="Base delivery fee")
    delivery_fee_per_km = models.DecimalField(max_digits=8, decimal_places=2, default=settings.DEFAULT_DELIVERY_FEE_PER_KM, help_text="Additional fee per kilometer")
    
    # Payment Methods
    accepts_cash = models.BooleanField(default=True)
    accepts_card = models.BooleanField(default=True)
    accepts_mobile_money = models.BooleanField(default=True)
    
    # SEO and Meta
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    
    # System Settings
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurant Settings"
        verbose_name_plural = "Restaurant Settings"

    def __str__(self):
        return f"{self.name} Settings"
    
    @property
    def coordinates(self):
        """Get restaurant coordinates in a convenient format."""
        if self.restaurant_latitude and self.restaurant_longitude:
            return {
                'latitude': float(self.restaurant_latitude),
                'longitude': float(self.restaurant_longitude),
                'location': {
                    'lat': float(self.restaurant_latitude),
                    'lng': float(self.restaurant_longitude)
                }
            }
        return None
    
    @property
    def coordinates_display(self):
        """Get coordinates in a readable string format."""
        if self.restaurant_latitude and self.restaurant_longitude:
            return f"{self.restaurant_latitude}, {self.restaurant_longitude}"
        return "Not set"

    @classmethod
    def get_settings(cls):
        restaurant_settings, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'name': "Chopsticks and Bowls",
                'description': "Authentic Korean Cuisine in Abuja",
                'tagline': "Authentic Korean Cuisine in Abuja",
                'address': "Abuja, Nigeria",
                'phone': "+234",
                'email': "info@chopsticksandbowls.com",
                'website': "https://chopsticksandbowls.com",
                'restaurant_latitude': 9.0820,
                'restaurant_longitude': 7.3986,
                'opening_hours': {},
                'instagram_url': "https://instagram.com/chop.sticksandbowls",
                'delivery_radius': 10.00,
                'minimum_order': 0.00,
                'free_delivery_threshold': 50.00,
                'vat_rate': 0.075,
                'pickup_delivery_fee': 0.00,
                'delivery_fee_base': settings.DEFAULT_DELIVERY_FEE_BASE,
                'delivery_fee_per_km': settings.DEFAULT_DELIVERY_FEE_PER_KM,
                'accepts_cash': True,
                'accepts_card': True,
                'accepts_mobile_money': True,
            }
        )
        return restaurant_settings

    @classmethod
    def get_delivery_settings(cls):
        """Returns delivery-related settings as a dictionary"""
        restaurant_settings = cls.get_settings()
        return {
            'pickup_delivery_fee': restaurant_settings.pickup_delivery_fee,
            'delivery_fee_base': restaurant_settings.delivery_fee_base,
            'delivery_fee_per_km': restaurant_settings.delivery_fee_per_km,
            'delivery_radius': restaurant_settings.delivery_radius,
            'minimum_order': restaurant_settings.minimum_order,
            'free_delivery_threshold': restaurant_settings.free_delivery_threshold,
        }
