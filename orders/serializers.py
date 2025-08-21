from rest_framework import serializers
from .models import Order, OrderItem
from decimal import Decimal
import decimal
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_minimum_order_amount():
    """Get minimum order amount from RestaurantSettings or fallback to Django settings."""
    try:
        from core.models import RestaurantSettings
        restaurant_settings = RestaurantSettings.get_settings()
        return restaurant_settings.minimum_order
    except Exception:
        # Fallback to Django settings
        return getattr(settings, 'MINIMUM_ORDER_AMOUNT', Decimal('1000.00'))


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


class UnifiedOrderSerializer(serializers.ModelSerializer):
    """Unified serializer for order creation (both authenticated and guest users)."""
    
    items = OrderItemSerializer(many=True)
    
    # Customer information fields (mandatory for all orders)
    customer_name = serializers.CharField(max_length=200, required=True, help_text="Customer's full name")
    customer_email = serializers.EmailField(required=True, help_text="Customer's email address")
    customer_phone = serializers.CharField(max_length=15, required=True, help_text="Customer's phone number")
    
    # Delivery address as string for guest users
    delivery_address = serializers.CharField(max_length=500, required=False, allow_blank=True, help_text="Delivery address as text (required for delivery orders)")
    
    # Reward and promotion fields
    reward_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID of the reward to apply")
    promo_code = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True, help_text="Promotional code to apply")
    
    # Order details
    order_note = serializers.CharField(max_length=500, required=False, allow_blank=True, help_text="Additional notes for the order")
    
    # Make total fields required for frontend validation
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, help_text='Delivery fee amount (0 for pickup orders)')
    discount_amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), help_text='Discount amount to apply')
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_email', 'customer_phone',
            'delivery_address', 'delivery_type', 'special_instructions', 'items',
            'reward_id', 'promo_code', 'order_note',
            'subtotal', 'tax_amount', 'delivery_fee', 'discount_amount', 'total_amount'
        ]
    
    def validate_total_amount(self, value):
        """Validate minimum order amount."""
        minimum_order = get_minimum_order_amount()
        if value < minimum_order:
            raise serializers.ValidationError(f"Minimum order amount is ₦{minimum_order:.2f}")
        return value
    
    def validate(self, data):
        """Validate order data and calculate totals."""
        minimum_order = get_minimum_order_amount()
        
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
    
    def _calculate_reward_discount(self, data):
        """Calculate discount amount based on reward_id if provided."""
        reward_id = data.get('reward_id')
        print(f"🔍 STEP 1: Starting reward discount calculation")
        print(f"   - reward_id from data: {reward_id}")
        print(f"   - data keys: {list(data.keys())}")
        
        if not reward_id:
            print(f"   ❌ No reward_id provided, returning 0.00")
            return Decimal('0.00')
        
        print(f"   ✅ reward_id found: {reward_id}")
        
        try:
            from loyalty.models import UserReward
            print(f"🔍 STEP 2: Importing UserReward model")
            
            # Get the user reward
            request = self.context.get('request')
            print(f"🔍 STEP 3: Getting request context")
            print(f"   - request exists: {request is not None}")
            
            if not request:
                print(f"   ❌ No request context found")
                raise serializers.ValidationError({
                    'reward_id': 'Request context not available for reward validation'
                })
                
            if not request.user.is_authenticated:
                print(f"   ❌ User not authenticated")
                raise serializers.ValidationError({
                    'reward_id': 'User must be authenticated to use rewards'
                })
            
            print(f"   ✅ User authenticated: {request.user.id} ({request.user.email})")
            
            try:
                print(f"🔍 STEP 4: Looking up UserReward in database")
                print(f"   - Searching for: id={reward_id}, user={request.user.id}, status='active'")
                
                user_reward = UserReward.objects.get(
                    id=reward_id,
                    user=request.user,
                    status='active'
                )
                print(f"   ✅ UserReward found: {user_reward.id}")
                print(f"   - Status: {user_reward.status}")
                print(f"   - Created: {user_reward.redeemed_at}")
                print(f"   - Expires: {user_reward.expires_at}")
                
            except UserReward.DoesNotExist:
                print(f"   ❌ UserReward not found in database")
                # Let's check what UserRewards exist for this user
                user_rewards = UserReward.objects.filter(user=request.user)
                print(f"   - User {request.user.id} has {user_rewards.count()} UserRewards:")
                for ur in user_rewards:
                    print(f"     * ID: {ur.id}, Status: {ur.status}, Reward: {ur.reward.name if ur.reward else 'Unknown'}")
                
                raise serializers.ValidationError({
                    'reward_id': f'Reward {reward_id} not found or not active for your account'
                })
            
            # Check if reward is expired
            print(f"🔍 STEP 5: Checking if reward is expired")
            print(f"   - is_expired property: {user_reward.is_expired}")
            
            if user_reward.is_expired:
                print(f"   ❌ Reward is expired")
                raise serializers.ValidationError({
                    'reward_id': f'Reward {reward_id} has expired and cannot be used'
                })
            
            print(f"   ✅ Reward is not expired")
            
            # Calculate discount based on reward type
            reward = user_reward.reward
            print(f"🔍 STEP 6: Processing reward details")
            print(f"   - Reward name: {reward.name}")
            print(f"   - Reward type: {reward.reward_type}")
            print(f"   - Discount percentage: {reward.discount_percentage}")
            print(f"   - Discount amount: {reward.discount_amount}")
            
            if reward.reward_type == 'discount':
                print(f"🔍 STEP 7: Processing discount type reward")
                if reward.discount_percentage:
                    # Calculate percentage discount based on subtotal
                    subtotal = Decimal(str(data.get('subtotal', 0)))
                    discount_amount = subtotal * (reward.discount_percentage / 100)
                    print(f"   ✅ Applied percentage discount: {reward.discount_percentage}% on subtotal {subtotal} = {discount_amount}")
                    return discount_amount
                else:
                    print(f"   ❌ Reward has discount type but no discount value")
                    raise serializers.ValidationError({
                        'reward_id': f'Reward {reward_id} has invalid discount configuration'
                    })
            elif reward.reward_type == 'free_delivery':
                # Free delivery reward - discount is the delivery fee
                delivery_fee = Decimal(str(data.get('delivery_fee', 0)))
                print(f"   ✅ Applied free delivery reward: discount = delivery fee {delivery_fee}")
                return delivery_fee
            elif reward.reward_type == 'cashback':
                # Cashback reward - doesn't affect order total but should be validated
                print(f"   ✅ Cashback reward validated: {reward.name}")
                print(f"   - Cashback amount: {reward.discount_amount}")
                # Cashback rewards don't affect the order total calculation
                return reward.discount_amount
            elif reward.reward_type == 'free_item':
                # Free item reward - doesn't affect order total but should be validated
                print(f"   ✅ Free item reward validated: {reward.name}")
                print(f"   - Free item: {reward.free_item.name if reward.free_item else 'Not specified'}")
                # Free item rewards don't affect the order total calculation
                return Decimal('0.00')
            else:
                # Other reward types don't affect order total
                print(f"   ⚠️ Unknown reward type {reward.reward_type} - no discount applied")
                return Decimal('0.00')
                
        except serializers.ValidationError:
            # Re-raise validation errors
            print(f"   ❌ Validation error raised, re-raising")
            raise
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
            import traceback
            print(f"   - Traceback: {traceback.format_exc()}")
            raise serializers.ValidationError({
                'reward_id': f'Error processing reward {reward_id}: {str(e)}'
            })
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Extract customer information
        customer_name = validated_data.pop('customer_name')
        customer_email = validated_data.pop('customer_email')
        customer_phone = validated_data.pop('customer_phone')
        
        # Extract delivery address (now as string)
        delivery_address_text = validated_data.pop('delivery_address', '')
        
        # Extract fields that don't exist in Order model
        reward_id = validated_data.pop('reward_id', None)
        promo_code = validated_data.pop('promo_code', None)
        order_note = validated_data.pop('order_note', '')
        
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
        minimum_order = get_minimum_order_amount()
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
            validated_data = self._calculate_backend_totals(validated_data, items_data)
            
            # Re-validate minimum order amount after backend calculation
            if validated_data['total_amount'] < minimum_order:
                raise serializers.ValidationError({
                    'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}. Please add more items to your order.'
                })
        
        # Handle user assignment based on authentication
        request = self.context.get('request')
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
        
        # For delivery orders, store the address text in special_instructions if no address ID
        if validated_data.get('delivery_type') == 'delivery' and delivery_address_text:
            current_instructions = validated_data.get('special_instructions', '')
            address_info = f"Delivery Address: {delivery_address_text}"
            
            # Add order note if provided
            if order_note:
                address_info = f"{address_info}\n\nOrder Note: {order_note}"
            
            if current_instructions:
                validated_data['special_instructions'] = f"{current_instructions}\n\n{address_info}"
            else:
                validated_data['special_instructions'] = address_info
        elif order_note:
            # If no delivery address but order note exists, add it to special instructions
            current_instructions = validated_data.get('special_instructions', '')
            if current_instructions:
                validated_data['special_instructions'] = f"{current_instructions}\n\nOrder Note: {order_note}"
            else:
                validated_data['special_instructions'] = f"Order Note: {order_note}"
        
        # Create the order with calculated totals
        order = Order.objects.create(**validated_data)
        
        # Apply reward if reward_id was provided
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
            except Exception as e:
                # Log the error but don't fail the order creation
                logger.error(f"Error applying reward {reward_id} to order {order.id}: {str(e)}")
        
        # Create order items with graceful error handling
        for item_data in items_data:
            try:
                menu_item = item_data['menu_item']
                item_data['unit_price'] = menu_item.price
                item_data['total_price'] = menu_item.price * item_data['quantity']
                OrderItem.objects.create(order=order, **item_data)
            except Exception as e:
                # Log the error but continue with other items
                logger.error(f"Error creating order item: {e}")
                continue
        
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
            
            # Check minimum order amount
            minimum_order = get_minimum_order_amount()
            if total < minimum_order:
                return False
            
            return True
            
        except (ValueError, TypeError, decimal.InvalidOperation):
            return False
    
    def _calculate_backend_totals(self, validated_data, items_data):
        """Calculate backend totals as fallback"""
        # Calculate subtotal from items
        subtotal = sum(item['quantity'] * item['menu_item'].price for item in items_data)
        
        # Get restaurant settings for tax calculation
        try:
            from core.models import RestaurantSettings
            settings = RestaurantSettings.get_settings()
            vat_rate = settings.vat_rate
        except Exception:
            vat_rate = Decimal('0.075')  # Default 7.5% VAT
        
        # Calculate tax
        tax_amount = subtotal * vat_rate
        
        # Get delivery fee from validated data or default to 0
        delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        
        # Get discount amount from validated data or default to 0
        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        
        # Calculate total
        total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        # Ensure minimum order amount
        minimum_order = get_minimum_order_amount()
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


class GuestOrderSerializer(serializers.ModelSerializer):
    """Serializer specifically for guest order creation."""
    
    items = OrderItemSerializer(many=True)
    
    # Make total fields required for frontend validation
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, help_text='Delivery fee amount (0 for pickup orders)')
    discount_amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), help_text='Discount amount to apply')
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    
    class Meta:
        model = Order
        fields = [
            'guest_email', 'guest_name', 'guest_phone', 'delivery_address', 
            'delivery_type', 'special_instructions', 'items',
            'subtotal', 'tax_amount', 'delivery_fee', 'discount_amount', 'total_amount'
        ]
    
    def validate_total_amount(self, value):
        """Validate minimum order amount."""
        minimum_order = get_minimum_order_amount()
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
        """Validate guest order data including totals."""
        minimum_order = get_minimum_order_amount()
        
        if not data.get('guest_email'):
            raise serializers.ValidationError("Guest email is required.")
        if not data.get('guest_name'):
            raise serializers.ValidationError("Guest name is required.")
        if not data.get('guest_phone'):
            raise serializers.ValidationError("Guest phone is required.")
        
        # Validate delivery_fee is 0 for pickup orders
        delivery_type = data.get('delivery_type')
        delivery_fee = data.get('delivery_fee', 0)
        if delivery_type == 'pickup' and delivery_fee != 0:
            raise serializers.ValidationError({
                'delivery_fee': 'Delivery fee must be 0 for pickup orders.'
            })
        
        # Validate items
        if not data.get('items'):
            raise serializers.ValidationError("Order must contain at least one item.")
        
        # Validate minimum order amount
        if data.get('total_amount', 0) < minimum_order:
            raise serializers.ValidationError({
                'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}'
            })
        
        # Validate that discount doesn't exceed order value
        subtotal = Decimal(str(data.get('subtotal', 0)))
        tax = Decimal(str(data.get('tax_amount', 0)))
        delivery_fee = Decimal(str(data.get('delivery_fee', 0)))
        discount = Decimal(str(data.get('discount_amount', 0)))
        total = Decimal(str(data.get('total_amount', 0)))
        
        # Check basic math with better precision handling
        calculated_total = subtotal + tax + delivery_fee - discount
        if abs(calculated_total - total) > Decimal('0.01'):  # Allow for rounding
            logger.warning(f"Total calculation mismatch: calculated={calculated_total}, received={total}, diff={abs(calculated_total - total)}")
            raise serializers.ValidationError({
                'total_amount': 'Total amount calculation is incorrect'
            })
        
        # Check discount doesn't exceed order value
        max_discount = subtotal + tax + delivery_fee
        if discount > max_discount:
            raise serializers.ValidationError({
                'discount_amount': 'Discount cannot exceed order value'
            })
        
        return data
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Extract frontend-calculated totals
        frontend_subtotal = validated_data.get('subtotal')
        frontend_tax = validated_data.get('tax_amount')
        frontend_delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        frontend_discount = validated_data.get('discount_amount', Decimal('0.00'))
        frontend_total = validated_data.get('total_amount')
        
        # Validate minimum order amount
        minimum_order = get_minimum_order_amount()
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
            validated_data = self._calculate_backend_totals(validated_data, items_data)
            
            # Re-validate minimum order amount after backend calculation
            if validated_data['total_amount'] < minimum_order:
                raise serializers.ValidationError({
                    'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}. Please add more items to your order.'
                })
        
        # Create the order with calculated totals
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            menu_item = item_data['menu_item']
            item_data['unit_price'] = menu_item.price
            item_data['total_price'] = menu_item.price * item_data['quantity']
            OrderItem.objects.create(order=order, **item_data)
        
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
            
            # Check minimum order amount
            minimum_order = get_minimum_order_amount()
            if total < minimum_order:
                return False
            
            return True
            
        except (ValueError, TypeError, decimal.InvalidOperation):
            return False
    
    def _calculate_backend_totals(self, validated_data, items_data):
        """Calculate backend totals as fallback"""
        # Calculate subtotal from items
        subtotal = sum(item['quantity'] * item['menu_item'].price for item in items_data)
        
        # Get restaurant settings for tax calculation
        try:
            from core.models import RestaurantSettings
            settings = RestaurantSettings.get_settings()
            vat_rate = settings.vat_rate
        except Exception:
            vat_rate = Decimal('0.075')  # Default 7.5% VAT
        
        # Calculate tax
        tax_amount = subtotal * vat_rate
        
        # Get delivery fee from validated data or default to 0
        delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        
        # Get discount amount from validated data or default to 0
        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        
        # Calculate total
        total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        # Ensure minimum order amount
        minimum_order = get_minimum_order_amount()
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
        minimum_order = get_minimum_order_amount()
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
        minimum_order = get_minimum_order_amount()
        
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
        minimum_order = get_minimum_order_amount()
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
            validated_data = self._calculate_backend_totals(validated_data, items_data)
            
            # Re-validate minimum order amount after backend calculation
            if validated_data['total_amount'] < minimum_order:
                raise serializers.ValidationError({
                    'total_amount': f'Minimum order amount is ₦{minimum_order:.2f}. Please add more items to your order.'
                })
        
        # Create the order with validated totals
        order = Order.objects.create(**validated_data)
        
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
        
        # Create order items
        for item_data in items_data:
            menu_item = item_data['menu_item']
            item_data['unit_price'] = menu_item.price
            item_data['total_price'] = menu_item.price * item_data['quantity']
            OrderItem.objects.create(order=order, **item_data)
        
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
            
            # Check minimum order amount
            minimum_order = get_minimum_order_amount()
            if total < minimum_order:
                return False
            
            return True
            
        except (ValueError, TypeError, decimal.InvalidOperation):
            return False
    
    def _calculate_backend_totals(self, validated_data, items_data):
        """Calculate backend totals as fallback"""
        # Calculate subtotal from items
        subtotal = sum(item['quantity'] * item['menu_item'].price for item in items_data)
        
        # Get restaurant settings for tax calculation
        try:
            from core.models import RestaurantSettings
            settings = RestaurantSettings.get_settings()
            vat_rate = settings.vat_rate
        except Exception:
            vat_rate = Decimal('0.075')  # Default 7.5% VAT
        
        # Calculate tax
        tax_amount = subtotal * vat_rate
        
        # Get delivery fee from validated data or default to 0
        delivery_fee = validated_data.get('delivery_fee', Decimal('0.00'))
        
        # Get discount amount from validated data or default to 0
        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        
        # Calculate total
        total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        # Ensure minimum order amount
        minimum_order = get_minimum_order_amount()
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


class CartItemSerializer(serializers.Serializer):
    """Serializer for cart items."""
    
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    special_instructions = serializers.CharField(required=False, allow_blank=True)


class CartCalculationSerializer(serializers.Serializer):
    """Serializer for cart total calculation."""
    
    items = CartItemSerializer(many=True)
    delivery_type = serializers.ChoiceField(choices=Order.DELIVERY_TYPE_CHOICES, default='delivery')
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0, help_text='Delivery fee amount (0 for pickup orders)')
    promotion_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reward_id = serializers.IntegerField(required=False, allow_null=True, help_text='UserReward ID to apply')
    
    def validate_items(self, value):
        """Validate cart items."""
        if not value:
            raise serializers.ValidationError("Cart must contain at least one item.")
        return value


class DeliveryFeeCalculationSerializer(serializers.Serializer):
    """Serializer for delivery fee calculation."""
    
    delivery_address = serializers.CharField(max_length=500, help_text="Delivery address as text")
    delivery_type = serializers.ChoiceField(choices=Order.DELIVERY_TYPE_CHOICES, default='delivery')


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status."""
    
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    estimated_delivery_time = serializers.DateTimeField(required=False)
