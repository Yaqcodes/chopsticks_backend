from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid
from core.models import RestaurantSettings
from decimal import Decimal


def generate_order_number(restaurant_settings, max_retries=5):
    """
    Generate a unique order number per business in format ORD-001.
    
    Uses database-level locking (SELECT FOR UPDATE) to prevent race conditions.
    Implements retry logic for concurrent order creation.
    
    Args:
        restaurant_settings: RestaurantSettings instance (required for multi-tenant)
        max_retries: Maximum number of retry attempts (default: 5)
    
    Returns:
        str: Unique order number for the business (e.g., "ORD-001")
    
    Raises:
        ValueError: If restaurant_settings is not provided
        RuntimeError: If unable to generate unique order number after retries
    """
    if not restaurant_settings:
        raise ValueError("restaurant_settings is required for tenant-scoped order number generation")
    
    from django.db import transaction
    import time
    import random
    
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Use SELECT FOR UPDATE to lock the row and prevent concurrent access
                # This ensures only one transaction can generate an order number at a time
                last_order = Order.objects.filter(
                    restaurant_settings=restaurant_settings
                ).select_for_update().order_by('-order_number').first()
                
    if last_order:
        # Extract number from last order number
        try:
            last_num = int(last_order.order_number.split('-')[1])
            new_num = last_num + 1
        except (IndexError, ValueError):
                        # If order number format is invalid, start from 1
            new_num = 1
    else:
                    # No previous orders for this business
        new_num = 1
    
                order_number = f"ORD-{new_num:03d}"
                
                # Verify uniqueness (double-check with database constraint)
                # This is a safety check - the unique_together constraint will catch duplicates
                exists = Order.objects.filter(
                    restaurant_settings=restaurant_settings,
                    order_number=order_number
                ).exists()
                
                if exists:
                    # If somehow a duplicate exists, increment and try again
                    new_num += 1
                    order_number = f"ORD-{new_num:03d}"
                
                return order_number
                
        except Exception as e:
            # Log the error but retry
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Error generating order number (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            
            if attempt < max_retries - 1:
                # Exponential backoff with jitter to prevent thundering herd
                wait_time = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                time.sleep(wait_time)
            else:
                # Last attempt failed
                raise RuntimeError(
                    f"Failed to generate unique order number after {max_retries} attempts. "
                    f"Last error: {str(e)}"
                )
    
    # Should never reach here, but just in case
    raise RuntimeError("Failed to generate unique order number")


class Order(models.Model):
    """Order model for customer orders."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    DELIVERY_TYPE_CHOICES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup'),
    ]
    
    # Order identification
    # Note: order_number is unique per business (restaurant_settings), not globally unique
    # Use unique_together constraint in Meta class
    order_number = models.CharField(max_length=20)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    
    # Customer information (for guest orders)
    guest_email = models.EmailField(blank=True, null=True)
    guest_name = models.CharField(max_length=200, blank=True, null=True)
    guest_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Order details
    delivery_address = models.CharField(max_length=500, blank=True, null=True, help_text="Delivery address as text (for guest orders)")
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE_CHOICES, default='delivery')
    special_instructions = models.TextField(blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    estimated_delivery_time = models.DateTimeField(blank=True, null=True)
    actual_delivery_time = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Paystack integration fields
    paystack_reference = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Paystack transaction reference")
    paystack_access_code = models.CharField(max_length=100, blank=True, null=True, help_text="Paystack access code for transaction")
    payment_verified_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when payment was verified")
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        # Order numbers are unique per business (tenant-scoped)
        unique_together = [('restaurant_settings', 'order_number')]
        # Add index for faster lookups
        indexes = [
            models.Index(fields=['restaurant_settings', 'order_number']),
            models.Index(fields=['restaurant_settings', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.get_customer_name()}"
    
    def save(self, *args, **kwargs):
        """
        Save order with automatic order number generation if not set.
        Ensures restaurant_settings is set before generating order number.
        """
        # Validate restaurant_settings is set
        if not self.restaurant_settings:
            raise ValueError(
                "Order must have restaurant_settings set before saving. "
                "This is required for multi-tenant order number generation."
            )
        
        # Generate order number if not set (only for new orders)
        if not self.order_number and not self.pk:
            self.order_number = generate_order_number(self.restaurant_settings)
        
        # Only calculate totals if the order has been saved and has items
        # This prevents the error when creating new orders
        if self.pk and hasattr(self, 'items'):
            # Ensure totals are calculated if they're not set
            if not self.subtotal or not self.total_amount:
                self._calculate_and_set_totals()
        
        super().save(*args, **kwargs)
    
    def _calculate_and_set_totals(self):
        """Calculate and set order totals if they're not already set."""
        if not self.subtotal:
            # Calculate subtotal from order items
            self.subtotal = sum(item.total_price for item in self.items.all())
        
        if not self.tax_amount:
            # Calculate tax using order's restaurant_settings
            if not self.restaurant_settings:
                raise ValueError("Order must have restaurant_settings to calculate tax")
            vat_rate = self.restaurant_settings.vat_rate
            self.tax_amount = self.subtotal * vat_rate
        
        if not self.total_amount:
            # Calculate total
            self.total_amount = self.subtotal + self.tax_amount + self.delivery_fee - self.discount_amount
    
    def get_customer_name(self):
        """Get customer name from user or guest information."""
        if self.user:
            return self.user.full_name
        return self.guest_name or 'Guest'
    
    def get_customer_email(self):
        """Get customer email from user or guest information."""
        if self.user:
            return self.user.email
        return self.guest_email
    
    def get_customer_phone(self):
        """Get customer phone from user or guest information."""
        if self.user:
            return self.user.phone
        return self.guest_phone
    
    @property
    def is_guest_order(self):
        """Check if this is a guest order."""
        return self.user is None
    
    def calculate_totals(self):
        """Calculate order totals including tax and delivery fees."""
        if not self.restaurant_settings:
            raise ValueError("Order must have restaurant_settings to calculate totals")
        vat_rate = self.restaurant_settings.vat_rate
        
        # Calculate subtotal
        subtotal = sum(item.total_price for item in self.items.all())
        
        # Calculate VAT
        tax_amount = subtotal * vat_rate
        
        # Calculate total
        total = subtotal + tax_amount + self.delivery_fee
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'tax_rate': vat_rate,
            'delivery_fee': self.delivery_fee,
            'total': total
        }
    
    def get_paystack_amount(self):
        """Convert total_amount from Naira to kobo for Paystack API"""
        return int(self.total_amount * 100)


class OrderItem(models.Model):
    """Individual items in an order."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    special_instructions = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} - {self.order.order_number}"
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    @property
    def item_name(self):
        """Get the menu item name."""
        return self.menu_item.name
