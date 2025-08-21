from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """Menu category model."""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


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
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='menu_items')
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    badges = models.JSONField(default=list, blank=True)  # Store badge types as list
    allergens = models.JSONField(default=list, blank=True)  # Store allergen list
    nutritional_info = models.JSONField(default=dict, blank=True)  # Store nutritional data
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    preparation_time = models.PositiveIntegerField(default=15, help_text='Preparation time in minutes')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
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
