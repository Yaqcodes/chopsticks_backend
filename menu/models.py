from django.db import models
from django.core.validators import MinValueValidator

from core.models import RestaurantSettings


class Category(models.Model):
    """Menu category model. Business-specific."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['sort_order', 'name']
        unique_together = [['restaurant_settings', 'slug']]
    
    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """Menu item model (food/beverage and apparel)."""
    
    # Badges for food/beverage tenants (Roschi, Chopsticks)
    BADGE_CHOICES_FOOD = [
        ('spicy', 'Spicy'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten Free'),
        ('popular', 'Popular'),
        ('new', 'New'),
        ('chef_special', 'Chef Special'),
    ]
    # Badges for apparel tenant (ZMall only)
    BADGE_CHOICES_ZMALL = [
        ('bestseller', 'Bestseller'),
        ('sale', 'Sale'),
    ]
    BADGE_CHOICES = BADGE_CHOICES_FOOD + BADGE_CHOICES_ZMALL

    GENDER_CHOICES = [
        ('men', 'Male'),
        ('women', 'Female'),
        ('unisex', 'Unisex'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
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
    image = models.ImageField(upload_to='menu_items/', blank=False, null=True)
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

    # Apparel-only fields (used by ZMall; leave blank for food tenants)
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        help_text='Target gender (apparel). Leave blank for food/beverage.',
    )
    sizes = models.JSONField(
        default=list,
        blank=True,
        help_text='Size options as list (e.g. ["S", "M", "L"]). For apparel.',
    )
    colors = models.JSONField(
        default=list,
        blank=True,
        help_text='Color options as list of {"name": "...", "hex": "#..."}. For apparel.',
    )
    images = models.JSONField(
        default=list,
        blank=True,
        help_text='Legacy: additional image URLs. Prefer MenuItemImage for uploads.',
    )

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['category', '-created_at', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
    
    @property
    def formatted_price(self):
        """Return formatted price."""
        return f"${self.price:.2f}"
    
    def get_badges_display(self):
        """Return badge choices for display."""
        return [choice[1] for choice in self.BADGE_CHOICES if choice[0] in self.badges]


class MenuItemImage(models.Model):
    """Additional product images (apparel). Primary image uses MenuItem.image."""
    
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='extra_images',
    )
    image = models.ImageField(upload_to='menu_items/extra/')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'id']
