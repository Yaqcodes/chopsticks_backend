### SERIALIZERS ###
class OrderSerializer(serializers.ModelSerializer):
    """Serializer for order creation and updates."""
    
    items = OrderItemSerializer(many=True)
    customer_name = serializers.CharField(read_only=True)
    customer_email = serializers.CharField(read_only=True)
    customer_phone = serializers.CharField(read_only=True)
    
    # Reward and promotion fields
    reward_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the reward to apply")
    
    # Make total fields required for frontend validation
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, help_text='Delivery fee amount (0 for pickup orders)')
    discount_amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), help_text='Discount amount to apply')
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'guest_email', 'guest_name', 'guest_phone',
            'delivery_address', 'delivery_type', 'special_instructions',
            'subtotal', 'tax_amount', 'delivery_fee', 'discount_amount', 'total_amount',
            'status', 'payment_status', 'estimated_delivery_time', 'actual_delivery_time',
            'created_at', 'updated_at', 'items', 'customer_name', 'customer_email', 'customer_phone',
            'reward_id'
        ]
        read_only_fields = [
            'id', 'order_number', 'status', 'payment_status', 'estimated_delivery_time', 'actual_delivery_time',
            'created_at', 'updated_at', 'customer_name', 'customer_email', 'customer_phone'
        ]
    
    def validate_total_amount(self, value):
        """Validate minimum order amount."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is required for multi-tenant business identification")
        restaurant_settings = get_business_from_request(request)
        minimum_order = restaurant_settings.minimum_order
        if value < minimum_order:
            raise serializers.ValidationError(f"Minimum order amount is ₦{minimum_order:.2f}")
        return value
    
    def validate_delivery_fee(self, value):
        """Validate delivery fee field."""
        if value is None:
            raise serializers.ValidationError("Delivery fee is required.")
        if value < 0:
            raise serializers.ValidationError("Delivery fee cannot be negative.")
        return value
    
    def validate(self, data):
        """Validate order data and calculate totals."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is required for multi-tenant business identification")
        restaurant_settings = get_business_from_request(request)
        minimum_order = restaurant_settings.minimum_order
        
        # Validate delivery_fee is 0 for pickup orders
        delivery_type = data.get('delivery_type')
        delivery_fee = data.get('delivery_fee', 0)
        if delivery_type == 'pickup' and delivery_fee != 0:
            raise serializers.ValidationError({
                'delivery_fee': 'Delivery fee must be 0 for pickup orders.'
            })
        
        # Validate minimum order amount
        total_amount = data.get('total_amount', 0)
        if total_amount < minimum_order:
            raise serializers.ValidationError({
                'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}'
            })
        
        # Validate delivery address is required for delivery orders
        if data.get('delivery_type') == 'delivery' and not data.get('delivery_address'):
            raise serializers.ValidationError({
                'delivery_address': 'Delivery address is required for delivery orders.'
            })
        
        # Validate items are present
        if not data.get('items'):
            raise serializers.ValidationError({
                'items': 'Order must contain at least one item.'
            })
        
        # Calculate reward discount if reward_id is provided
        reward_discount = self._calculate_reward_discount(data)
        
        # Extract values for validation
        subtotal = Decimal(str(data.get('subtotal', 0)))
        tax = Decimal(str(data.get('tax_amount', 0)))
        delivery_fee = Decimal(str(data.get('delivery_fee', 0)))
        total = Decimal(str(data.get('total_amount', 0)))
        
        # Calculate total with reward discount
        calculated_total = subtotal + tax + delivery_fee - reward_discount
        
        if abs(calculated_total - total) > Decimal('0.01'):  # Allow for rounding
            raise serializers.ValidationError({
                'total_amount': f'Total amount calculation is incorrect. Expected: {calculated_total}, Received: {total}'
            })
        
        # Check discount doesn't exceed order value
        max_discount = subtotal + tax + delivery_fee
        if reward_discount > max_discount:
            raise serializers.ValidationError({
                'discount_amount': 'Discount cannot exceed order value'
            })
        
        # Update data with calculated discount
        data['discount_amount'] = reward_discount
        
        return data
    
    def validate_special_instructions(self, value):
        """Validate special instructions field."""
        if value:
            # Ensure the value is a valid string and can be encoded to UTF-8
            try:
                # Convert to string if it's not already
                str_value = str(value)
                # Test UTF-8 encoding
                str_value.encode('utf-8')
                return str_value
            except (UnicodeEncodeError, UnicodeDecodeError):
                raise serializers.ValidationError("Special instructions contain invalid characters.")
        return value or ''
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError({'detail': 'Request context is required.'})
        restaurant_settings = get_business_from_request(request)
        validated_data['restaurant_settings'] = restaurant_settings
        for item_data in items_data:
            menu_item = item_data['menu_item']
            if menu_item.restaurant_settings != restaurant_settings:
                raise serializers.ValidationError({
                    'items': 'One or more items do not belong to this business.'
                })
        
        # Handle user assignment based on authentication
        customer_email = validated_data.get('customer_email')
        customer_name = validated_data.get('customer_name')
        customer_phone = validated_data.get('customer_phone')
        
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
            # Populate guest fields with user information for consistency
            validated_data['guest_email'] = customer_email
            validated_data['guest_name'] = customer_name
            validated_data['guest_phone'] = customer_phone
        else:
            # Guest order - set guest fields
            validated_data['guest_email'] = customer_email
            validated_data['guest_name'] = customer_name
            validated_data['guest_phone'] = customer_phone
            validated_data['user'] = None
        
        # Extract frontend-calculated totals
        frontend_subtotal = validated_data.get('subtotal')
        frontend_tax = validated_data.get('tax_amount')
        frontend_delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        frontend_discount = validated_data.get('discount_amount', Decimal('0.00'))
        frontend_total = validated_data.get('total_amount')
        
        # Ensure pickup orders always have 0 delivery fee
        delivery_type = validated_data.get('delivery_type')
        if delivery_type == 'pickup':
            frontend_delivery_fee = Decimal('0.00')
            validated_data['delivery_fee'] = Decimal('0.00')
            print(f"   🔒 Pickup order: Forced delivery_fee to 0")
        
        # Validate minimum order amount
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is required for multi-tenant business identification")
        restaurant_settings = get_business_from_request(request)
        minimum_order = restaurant_settings.minimum_order
        if frontend_total and frontend_total < minimum_order:
            raise serializers.ValidationError({
                'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}'
            })
        
        # Perform validation that totals are reasonable
        if self._validate_totals_reasonable(
            frontend_subtotal, 
            frontend_tax, 
            frontend_delivery_fee,
            frontend_discount,
            frontend_total
        ):
            # Use frontend totals as they are reasonable
            validated_data.update({
                'subtotal': frontend_subtotal,
                'tax_amount': frontend_tax,
                'delivery_fee': frontend_delivery_fee,
                'discount_amount': frontend_discount,
                'total_amount': frontend_total,
            })
        else:
            # Fall back to backend calculation for safety
            validated_data = self._calculate_backend_totals(validated_data, items_data, restaurant_settings)
            
            # Re-validate minimum order amount after backend calculation
            if validated_data['total_amount'] < minimum_order:
                raise serializers.ValidationError({
                    'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}. Please add more items to your order.'
                })
        
        # Create the order with validated totals using atomic transaction
        # This ensures order creation and order number generation are atomic
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Create the order - order number will be auto-generated in save()
                order = Order.objects.create(**validated_data)
                
                # Create order items within the same transaction
                for item_data in items_data:
                    OrderItem.objects.create(
                        order=order,
                        menu_item=item_data['menu_item'],
                        quantity=item_data['quantity'],
                        unit_price=item_data.get('unit_price', item_data['menu_item'].price),
                        total_price=item_data.get('total_price'),
                        special_instructions=item_data.get('special_instructions', '')
                    )
        except Exception as e:
            # Log the error and re-raise for proper error handling
            logger.error(f"Error creating order in transaction: {str(e)}")
            raise serializers.ValidationError({
                'detail': f'Failed to create order: {str(e)}'
            })
        
        # Apply reward if reward_id was provided
        reward_id = validated_data.get('reward_id')
        request = self.context.get('request')
        if reward_id and request and request.user.is_authenticated:
            try:
                from loyalty.models import UserReward
                user_reward = UserReward.objects.get(
                    id=reward_id,
                    user=request.user,
                    status='active'
                )
                
                # Mark the reward as used and link it to the order
                user_reward.use_reward(order)
                
                # Handle cashback rewards - award cashback to user's account
                if user_reward.reward.reward_type == 'cashback':
                    try:
                        from loyalty.models import UserPoints
                        user_points, created = UserPoints.objects.get_or_create(user=request.user)
                        
                        if user_reward.reward.cashback_percentage:
                            # Calculate cashback based on order subtotal
                            cashback_amount = order.subtotal * (user_reward.reward.cashback_percentage / 100)
                        elif user_reward.reward.cashback_amount:
                            # Use fixed cashback amount
                            cashback_amount = user_reward.reward.cashback_amount
                        else:
                            cashback_amount = Decimal('0.00')
                        
                        if cashback_amount > 0:
                            user_points.balance += cashback_amount
                            user_points.total_earned += cashback_amount
                            user_points.save()
                            print(f"   💰 Awarded cashback: {cashback_amount} to user {request.user.id}")
                    except Exception as e:
                        print(f"   ❌ Error awarding cashback: {str(e)}")
                
            except Exception as e:
                # Log the error but don't fail the order creation
                logger.error(f"Error applying reward {reward_id} to order {order.id}: {str(e)}")
        
        # Refresh the order to ensure all related fields are loaded
        order.refresh_from_db()
        
        return order
    
    def _validate_totals_reasonable(self, subtotal, tax, delivery_fee, discount, total):
        """Quick validation that totals are reasonable"""
        try:
            # Convert to Decimal for precise calculations
            subtotal = Decimal(str(subtotal)) if subtotal else Decimal('0')
            tax = Decimal(str(tax)) if tax else Decimal('0')
            delivery_fee = Decimal(str(delivery_fee)) if delivery_fee else Decimal('0')
            discount = Decimal(str(discount)) if discount else Decimal('0')
            total = Decimal(str(total)) if total else Decimal('0')
            
            # Check basic math: subtotal + tax + delivery_fee - discount = total
            calculated_total = subtotal + tax + delivery_fee - discount
            if abs(calculated_total - total) > Decimal('0.01'):  # Allow for rounding
                return False
            
            # Check subtotal is positive and reasonable
            if subtotal <= 0 or subtotal > 1000000:  # Max 1M Naira
                return False
            
            # Check tax rate is reasonable (e.g., between 0% and 25%)
            if subtotal > 0:
                tax_rate = tax / subtotal
                if not (Decimal('0') <= tax_rate <= Decimal('0.25')):
                    return False
            
            # Check delivery fee is reasonable (0 to 5000 Naira)
            if delivery_fee < 0 or delivery_fee > 5000:
                return False
            
            # Check discount is reasonable (0 to subtotal + tax + delivery_fee)
            max_discount = subtotal + tax + delivery_fee
            if discount < 0 or discount > max_discount:
                return False
            
            # Check total is positive and reasonable
            if total <= 0 or total > 1000000:  # Max 1M Naira
                return False
            
            # Check minimum order amount - requires restaurant_settings
            # This method should be called with restaurant_settings context
            # For now, skip minimum order check in this validation method
            # as it requires business context
            pass
            
            return True
            
        except (ValueError, TypeError, decimal.InvalidOperation):
            return False
    
    def _calculate_backend_totals(self, validated_data, items_data, restaurant_settings):
        """Calculate backend totals as fallback. restaurant_settings is REQUIRED for multi-tenant support."""
        if not restaurant_settings:
            raise ValueError("restaurant_settings is required for multi-tenant totals calculation")
        
        # Calculate subtotal from items
        subtotal = sum(item['quantity'] * item['menu_item'].price for item in items_data)
        
        # Get restaurant settings for tax calculation
        vat_rate = restaurant_settings.vat_rate
        
        # Calculate tax
        tax_amount = subtotal * vat_rate
        
        # Get delivery fee from validated data or default to 0
        delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        
        # Get discount amount from validated data or default to 0
        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        
        # Calculate total
        total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        # Ensure minimum order amount
        minimum_order = restaurant_settings.minimum_order
        if total_amount < minimum_order:
            # If total is below minimum, adjust discount to meet minimum
            max_discount = subtotal + tax_amount + delivery_fee - minimum_order
            discount_amount = min(discount_amount, max_discount)
            total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'delivery_fee': delivery_fee,
            'discount_amount': discount_amount,
            'total_amount': total_amount,
        }
    
    def _calculate_reward_discount(self, data):
        """Calculate discount amount based on reward_id if provided."""
        reward_id = data.get('reward_id')
        
        if not reward_id:
            return Decimal('0.00')
        
        try:
            from loyalty.models import UserReward
            request = self.context.get('request')
            
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError({
                    'reward_id': 'User must be authenticated to use rewards'
                })
            
            user_reward = UserReward.objects.get(
                id=reward_id,
                user=request.user,
                status='active'
            )
            
            if user_reward.is_expired:
                raise serializers.ValidationError({
                    'reward_id': f'Reward {reward_id} has expired and cannot be used'
                })
            
            # Calculate discount based on reward type
            reward = user_reward.reward
            
            if reward.reward_type == 'discount':
                if reward.discount_percentage:
                    # Calculate percentage discount based on subtotal
                    subtotal = Decimal(str(data.get('subtotal', 0)))
                    discount_amount = subtotal * (reward.discount_percentage / 100)
                    return discount_amount
                else:
                    raise serializers.ValidationError({
                        'reward_id': f'Reward {reward_id} has invalid discount configuration'
                    })
            elif reward.reward_type == 'free_delivery':
                # Free delivery reward - discount is the delivery fee
                delivery_fee = Decimal(str(data.get('delivery_fee', 0)))
                return delivery_fee
            elif reward.reward_type == 'cashback':
                # Cashback reward - doesn't affect order total but should be validated
                return reward.discount_amount
            elif reward.reward_type == 'free_item':
                # Free item reward - doesn't affect order total but should be validated
                return Decimal('0.00')
            else:
                # Other reward types don't affect order total
                return Decimal('0.00')
                
        except serializers.ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise serializers.ValidationError({
                'reward_id': f'Error processing reward {reward_id}: {str(e)}'
            })
    
    def to_representation(self, instance):
        """Custom representation to handle cases where items might not be loaded."""
        data = super().to_representation(instance)
        
        # Ensure items are properly loaded if they exist
        if hasattr(instance, 'items') and instance.pk:
            try:
                data['items'] = OrderItemSerializer(instance.items.all(), many=True).data
            except Exception:
                data['items'] = []
        else:
            data['items'] = []
        
        return data

class OrderItemSerializer(serializers.ModelSerializer):

    """Serializer for order items."""

    item_name = serializers.CharField(source='menu_item.name', read_only=True)

    item_description = serializers.CharField(source='menu_item.description', read_only=True)

    item_image = serializers.CharField(source='menu_item.image', read_only=True)

class Meta:

        model = OrderItem

        fields = [

'id', 'menu_item', 'item_name', 'item_description', 'item_image',

'quantity', 'unit_price', 'total_price', 'special_instructions'

]

        read_only_fields = ['id', 'unit_price', 'total_price']

def validate_special_instructions(self, value):

"""Validate special instructions field."""

if value:

# Ensure the value is a valid string and can be encoded to UTF-8

try:

# Convert to string if it's not already

                str_value = str(value)

# Test UTF-8 encoding

                str_value.encode('utf-8')

return str_value

except (UnicodeEncodeError, UnicodeDecodeError):

raise serializers.ValidationError("Special instructions contain invalid characters.")

return value or ''

def to_representation(self, instance):

"""Custom representation to handle cases where related fields might not be loaded."""

        data = super().to_representation(instance)

# Safely access related fields

try:

if instance.menu_item:

                data['item_name'] = instance.menu_item.name

                data['item_description'] = instance.menu_item.description

# Safely handle image field - convert to string URL or empty string

if instance.menu_item.image:

try:

# Get the URL string representation of the image

                        data['item_image'] = str(instance.menu_item.image.url) if hasattr(instance.menu_item.image, 'url') else str(instance.menu_item.image)

except Exception:

# Fallback to empty string if image serialization fails

                        data['item_image'] = ''

else:

                    data['item_image'] = ''

else:

                data['item_name'] = 'Unknown Item'

                data['item_description'] = ''

                data['item_image'] = ''

except Exception:

            data['item_name'] = 'Unknown Item'

            data['item_description'] = ''

            data['item_image'] = ''

return data


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list (user order history)."""
    
    customer_name = serializers.CharField(read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'delivery_type', 'status',
            'payment_status', 'total_amount', 'created_at', 'items_count'
        ]
        read_only_fields = ['id', 'order_number', 'customer_name', 'status', 'payment_status', 'total_amount', 'created_at']
    
    def get_items_count(self, obj):
        """Get count of items in the order."""
        return obj.items.count()


class OrderDetailSerializer(OrderSerializer):
    """Detailed serializer for order information."""
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields


### Model ###
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

    # Inventory: set True when SKU is decremented on payment success; cleared when order is refunded/cancelled
    stock_reduced = models.BooleanField(default=False, help_text="True after payment success reduced menu item SKU; restored on refund/cancel.")
    
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
        
        # Restore stock when order is refunded or cancelled (any code path that sets these)
        if self.pk and getattr(self, 'stock_reduced', False):
            if self.payment_status == 'refunded' or self.status == 'cancelled':
                from orders.services import restore_stock_for_order
                restore_stock_for_order(self)
        
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


### VIEWS ###
class AdminOrderListView(generics.ListAPIView):
    """Admin view to list all orders with filtering capabilities."""
    permission_classes = [IsAdminUser]
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'delivery_type']
    ordering_fields = ['created_at', 'total_amount', 'order_number', 'status']
    ordering = ['-created_at']
def get_queryset(self):
# Handle Swagger schema generation
if getattr(self, 'swagger_fake_view', False):
return Order.objects.none()
# Check if user is staff
if not self.request.user.is_staff:
return Order.objects.none()
        restaurant_settings = get_business_from_request(self.request)
        queryset = Order.objects.filter(restaurant_settings=restaurant_settings)
# Handle date filtering manually
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
if date_from:
try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
except ValueError:
# If date format is invalid, ignore the filter
pass
if date_to:
try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
except ValueError:
# If date format is invalid, ignore the filter
pass
return queryset
class AdminOrderDetailView(generics.RetrieveAPIView):
"""Admin view to get detailed information about any specific order."""
    permission_classes = [IsAdminUser]
    serializer_class = OrderDetailSerializer
def get_queryset(self):
# Handle Swagger schema generation
if getattr(self, 'swagger_fake_view', False):
return Order.objects.none()
# Check if user is staff
if not self.request.user.is_staff:
return Order.objects.none()
        restaurant_settings = get_business_from_request(self.request)
# Return all orders for this specific business instance. 
# The URL parameter (pk/id) will automatically pick the specific order from this queryset.
return Order.objects.filter(
restaurant_settings=restaurant_settings,
)


### URLS ###
path('admin/', views.AdminOrderListView.as_view(), name='admin_order_list'),
path('admin/<int:pk>/', views.AdminOrderDetailView.as_view(), name='order_detail')

