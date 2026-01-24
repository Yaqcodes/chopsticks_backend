from django.db import models
from django.core.validators import MinValueValidator

from core.models import RestaurantSettings


class Category(models.Model):
    """Menu category model - business-scoped."""
    
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='categories',
        help_text="Business this category belongs to"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['restaurant_settings', 'is_active', 'sort_order']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.restaurant_settings.name}"


class MenuItem(models.Model):
    """Menu item model."""
    
    BADGE_CHOICES = [
        ('spicy', 'Spicy'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten Free'),
        ('popular', 'Popular'),
        ('new', 'New'),
        ('chef_special', 'Chef Special'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    size = models.CharField(
        max_length=50,
        blank=True,
        help_text="Product size/variant (e.g., '24-pack 35cl', 'Pure Water')",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='menu_items')
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='menu_items',
    )
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    badges = models.JSONField(default=list, blank=True)  # Store badge types as list
    allergens = models.JSONField(default=list, blank=True)  # Store allergen list
    nutritional_info = models.JSONField(default=dict, blank=True)  # Store nutritional data
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    preparation_time = models.PositiveIntegerField(default=15, help_text='Preparation time in minutes')
    sku = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Stock Keeping Unit - available quantity',
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['category', 'sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
    
    @property
    def formatted_price(self):
        """Return formatted price."""
        return f"${self.price:.2f}"
    
    def get_badges_display(self):
        """Return badge choices for display."""
        return [choice[1] for choice in self.BADGE_CHOICES if choice[0] in self.badges]
