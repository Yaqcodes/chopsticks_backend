from decimal import Decimal
from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404
from .models import Order
from addresses.models import Address
from menu.models import MenuItem
from promotions.models import PromoCode
from utils.geocoding import calculate_distance
from core.models import RestaurantSettings


def calculate_delivery_fee(delivery_type, distance_km=None, subtotal=None):
    """
    Calculate delivery fee based on delivery type and distance.
    
    Args:
        delivery_type (str): 'delivery' or 'pickup'
        distance_km (float): Distance in kilometers for delivery
        subtotal (Decimal): Order subtotal for free delivery threshold
        
    Returns:
        Decimal: Calculated delivery fee
    """
    try:
        settings = RestaurantSettings.get_settings()
        
        if delivery_type == 'pickup':
            return settings.pickup_delivery_fee
        
        # For delivery orders
        if distance_km is None:
            return settings.delivery_fee_base
            
        # Calculate delivery fee based on distance
        delivery_fee = settings.delivery_fee_base + (distance_km * settings.delivery_fee_per_km)
        return max(delivery_fee, Decimal('0.00'))
        
    except Exception:
        # Fallback to Django settings if RestaurantSettings fails
        if delivery_type == 'pickup':
            return Decimal('0.00')
        
        if distance_km is None:
            return Decimal(str(django_settings.DELIVERY_FEE_BASE))
            
        delivery_fee = Decimal(str(django_settings.DELIVERY_FEE_BASE)) + (distance_km * Decimal(str(django_settings.DELIVERY_FEE_PER_KM)))
        return max(delivery_fee, Decimal('0.00'))


def calculate_cart_totals(cart_items, delivery_type='delivery', delivery_fee=Decimal('0.00'), 
                          promo_code=None, user_reward=None):
    """
    Calculate complete cart totals including tax and delivery fees.
    
    Args:
        cart_items (list): List of cart items with price and quantity
        delivery_type (str): 'delivery' or 'pickup'
        delivery_fee (Decimal): Delivery fee amount (0 for pickup orders)
        promo_code (str): Promotional code for discount
        user_reward (UserReward): Selected UserReward object for discount calculation
        
    Returns:
        dict: Complete totals breakdown
    """
    try:
        settings = RestaurantSettings.get_settings()
        vat_rate = settings.vat_rate
    except Exception:
        # Fallback to Django settings if RestaurantSettings fails
        vat_rate = Decimal(str(django_settings.DEFAULT_TAX_RATE))
    
    # Calculate subtotal
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Use the provided delivery fee directly
    delivery_fee = Decimal(delivery_fee)
    
    # Calculate VAT
    tax_amount = subtotal * vat_rate
    
    # Calculate total before discounts
    total = subtotal + tax_amount + delivery_fee
    
    # Apply promo code discount if provided
    discount_amount = Decimal('0.00')
    if promo_code:
        # TODO: Implement promo code logic
        pass
    
    # Calculate reward discount
    reward_discount = "0"  # Default as string
    if user_reward and user_reward.status == 'active':
        reward = user_reward.reward
        
        if reward.reward_type == 'free_item':
            reward_discount = "FREE ITEM"
        elif reward.reward_type == 'cashback':
            if reward.discount_amount:
                reward_discount = str(reward.discount_amount)
            else:
                reward_discount = "0"
        elif reward.reward_type == 'discount':
            if reward.discount_percentage:
                discount_value = subtotal * (reward.discount_percentage / 100)
                reward_discount = str(discount_value)
            elif reward.discount_amount:
                reward_discount = str(reward.discount_amount)
            else:
                reward_discount = "0"
        elif reward.reward_type == 'free_delivery':
            reward_discount = str(delivery_fee)
    
    # Add reward discount to total discount amount (for calculation purposes)
    total_reward_discount = Decimal('0.00')
    if reward_discount not in ["0", "FREE ITEM"]:
        try:
            total_reward_discount = Decimal(reward_discount)
        except:
            total_reward_discount = Decimal('0.00')
    elif reward_discount == "FREE ITEM" and cart_items:
        # For free item, discount nothing
        # cheapest_item_price = min(item['price'] for item in cart_items)
        total_reward_discount = 0
        
    # Calculate final total
    discount_amount = discount_amount + total_reward_discount
    final_total = total - discount_amount
    if final_total < django_settings.MINIMUM_ORDER_AMOUNT:
        try:
            final_total = settings.minimum_order
        except Exception:
            final_total = django_settings.MINIMUM_ORDER_AMOUNT
    
    return {
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'tax_rate': vat_rate,
        'delivery_fee': delivery_fee,
        'discount_amount': discount_amount,
        'reward_discount': reward_discount,  # String format as requested
        'total': final_total,
        'delivery_type': delivery_type
    }


def process_order_payment(order, payment_method, payment_data=None):
    """Process order payment through appropriate gateway"""
    if payment_method == 'cash':
        # Cash payments are processed on delivery
        order.payment_status = 'pending'
        order.save()
        return True, "Cash payment will be collected on delivery"
    
    elif payment_method == 'online':
        # Redirect to Paystack for online payments
        from payments.services import PaystackService
        try:
            paystack = PaystackService()
            result = paystack.initialize_transaction(
                email=order.get_customer_email(),
                amount_kobo=order.get_paystack_amount(),
                order_number=order.order_number,
                callback_url=django_settings.PAYSTACK_CALLBACK_URL
            )
            
            # Store Paystack reference in order
            order.paystack_reference = result['reference']
            order.paystack_access_code = result['access_code']
            order.save()
            
            return True, result['authorization_url']
            
        except Exception as e:
            order.payment_status = 'failed'
            order.save()
            return False, f"Payment initialization failed: {str(e)}"
    
    else:
        return False, "Unsupported payment method"


def validate_order_items(items):
    """Validate order items for availability and pricing."""
    
    errors = []
    
    for item_data in items:
        try:
            menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
            
            # Check if item is available
            if not menu_item.is_available:
                errors.append(f"Item '{menu_item.name}' is not available")
            
            # Check if price matches (in case of price changes)
            if menu_item.price != item_data.get('unit_price', menu_item.price):
                errors.append(f"Price for '{menu_item.name}' has changed")
            
        except MenuItem.DoesNotExist:
            errors.append(f"Menu item with ID {item_data['menu_item_id']} not found")
    
    return errors


def estimate_delivery_time(order):
    """Estimate delivery time for an order."""
    
    from datetime import datetime, timedelta
    
    # Base preparation time
    preparation_time = 20  # minutes
    
    # Add time based on order complexity
    total_items = sum(item.quantity for item in order.items.all())
    if total_items > 5:
        preparation_time += 10
    
    # Add delivery time if applicable
    if order.delivery_type == 'delivery':
        delivery_time = 15  # minutes
        preparation_time += delivery_time
    
    # Calculate estimated time
    estimated_time = datetime.now() + timedelta(minutes=preparation_time)
    
    return estimated_time
