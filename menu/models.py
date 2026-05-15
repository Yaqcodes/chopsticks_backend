from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.models import RestaurantSettings


class Category(models.Model):
    """Menu category model. Business-specific."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    show_in_men = models.BooleanField(
        default=False,
        help_text='List this category under the Men nav tab.',
    )
    show_in_women = models.BooleanField(
        default=False,
        help_text='List this category under the Women nav tab.',
    )
    show_in_unisex = models.BooleanField(
        default=False,
        help_text='List in both Men and Women nav (shared / unisex shelf).',
    )
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


class Product(models.Model):
    """
    Grouped parent catalog row for Zmall (explicitly linked MenuItems are variants/SKUs).
    base_price is informational only; checkout uses MenuItem.price per variant.
    """

    BADGE_CHOICES_ZMALL = [
        ('bestseller', 'Bestseller'),
        ('sale', 'Sale'),
        ('preorder', 'Pre-Order'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=160, blank=True)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='catalog_products')
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='catalog_products',
    )
    gender = models.CharField(
        max_length=20,
        choices=[('men', 'Male'), ('women', 'Female'), ('unisex', 'Unisex')],
        blank=True,
        null=True,
        help_text='Shown on storefront; distinct from MenuItem apparel fields.',
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=Decimal('0.00'),
        help_text='Informational listing price only; variants charge MenuItem.price.',
    )
    badges = models.JSONField(default=list, blank=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Zmall Catalog Product'
        verbose_name_plural = 'Zmall Catalog Products'
        ordering = ['sort_order', '-created_at', 'name']
        unique_together = [['restaurant_settings', 'slug']]
        indexes = [
            models.Index(fields=['restaurant_settings', 'is_available']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        allowed = {c[0] for c in self.BADGE_CHOICES_ZMALL}
        if self.badges and isinstance(self.badges, list):
            unknown = [b for b in self.badges if b not in allowed]
            if unknown:
                raise ValidationError({'badges': 'Only bestseller, sale, and preorder badges are allowed.'})

    def get_effective_price(self):
        """Returns base_price (informational; checkout uses MenuItem.price)."""
        return self.base_price if self.base_price is not None else Decimal('0.00')

    def get_badges_display(self):
        display = dict(self.BADGE_CHOICES_ZMALL)
        allowed = set(display.keys())
        return [display.get(b, b) for b in (self.badges or []) if b in allowed]


class ProductImage(models.Model):
    """Gallery images for a grouped Product."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery_images',
    )
    image = models.ImageField(upload_to='products/')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'


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
    # Badges for apparel tenant (Zmall only)
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
    on_sale = models.BooleanField(
        default=False,
        help_text='When True, customers pay sale_price (must be set). Source of truth for sale state.',
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Discounted price when on_sale is True.',
    )
    product = models.ForeignKey(
        'Product',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='variants',
        help_text='Zmall grouped product parent; manual link only. Leave blank for non-grouped SKUs.',
    )
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

    # Product unique identifier
    barcode = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        unique=True,
        help_text="Product barcode (UPC, EAN, or custom QR string)."
    )

    # Apparel-only fields (used by Zmall; leave blank for food tenants)
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
        indexes = [
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.name} - {self.category.name}"

    def clean(self):
        super().clean()
        if self.on_sale:
            if self.sale_price is None:
                raise ValidationError({'sale_price': 'Sale price is required when the product is on sale.'})
            if self.sale_price >= self.price:
                raise ValidationError({'sale_price': 'Sale price must be less than list price.'})
        if self.product_id and self.restaurant_settings_id:
            if self.product.restaurant_settings_id != self.restaurant_settings_id:
                raise ValidationError(
                    {'product': 'Grouped catalog Product must belong to the same business as this SKU.'},
                )
            from menu.variant_utils import variant_keys

            new_keys = variant_keys(self)
            qs = MenuItem.objects.filter(product_id=self.product_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            for other in qs.iterator():
                if variant_keys(other) & new_keys:
                    raise ValidationError(
                        {'product': 'Another linked variant already uses this size/colour combination.'},
                    )

    def get_effective_price(self):
        """Unit price charged at checkout (list price unless on sale with sale_price set)."""
        if self.on_sale and self.sale_price is not None:
            return self.sale_price
        return self.price if self.price is not None else Decimal('0.00')
    
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


class ProductVariantLinkEvent(models.Model):
    """Audit trail for manual Product ↔ MenuItem linking."""

    created_at = models.DateTimeField(auto_now_add=True)
    acting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='variant_link_events',
    )
    action = models.CharField(max_length=20)
    product_id = models.BigIntegerField(null=True, blank=True)
    menu_item_id = models.BigIntegerField()
    previous_product_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Variant link event'
        verbose_name_plural = 'Variant link events'
