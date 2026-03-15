from decimal import Decimal
from django.conf import settings as django_settings
from django.db.models import F
from django.shortcuts import get_object_or_404
from .models import Order
from addresses.models import Address
from menu.models import MenuItem
from promotions.models import PromoCode
from utils.geocoding import calculate_distance
from core.models import RestaurantSettings


class InsufficientStockError(Exception):
    """Raised when an order item's menu_item has insufficient SKU to fulfill the order."""
    def __init__(self, message, menu_item=None, quantity=None):
        self.menu_item = menu_item
        self.quantity = quantity
        super().__init__(message)


def reduce_stock_for_order(order):
    """
    Decrement MenuItem.sku by each order item's quantity. Idempotent: no-op if order.stock_reduced.
    Call only from within a transaction with order locked (select_for_update).
    Raises InsufficientStockError if any item has insufficient stock; transaction should roll back.
    """
    if getattr(order, 'stock_reduced', False):
        return
    for item in order.items.select_related('menu_item').all():
        menu_item = item.menu_item
        qty = item.quantity
        updated = MenuItem.objects.filter(
            pk=menu_item.pk,
            sku__gte=qty,
        ).update(sku=F('sku') - qty)
        if updated != 1:
            raise InsufficientStockError(
                f"Insufficient stock for '{menu_item.name}' (need {qty}, has {menu_item.sku})",
                menu_item=menu_item,
                quantity=qty,
            )
    order.stock_reduced = True


def restore_stock_for_order(order):
    """
    Restore MenuItem.sku by adding back each order item's quantity. No-op if not order.stock_reduced.
    Call when order is refunded or cancelled (e.g. from Order.save() or when updating status).
    """
    if not getattr(order, 'stock_reduced', False):
        return
    for item in order.items.select_related('menu_item').all():
        MenuItem.objects.filter(pk=item.menu_item_id).update(
            sku=F('sku') + item.quantity
        )
    order.stock_reduced = False


def calculate_delivery_fee(delivery_type, distance_km=None, subtotal=None, restaurant_settings=None):
    """
    Calculate delivery fee based on delivery type and distance.
    
    Args:
        delivery_type (str): 'delivery' or 'pickup'
        distance_km (float): Distance in kilometers for delivery
        subtotal (Decimal): Order subtotal for free delivery threshold
        restaurant_settings (RestaurantSettings): REQUIRED - Business settings for multi-tenant support
        
    Returns:
        Decimal: Calculated delivery fee
    
    Raises:
        ValueError: If restaurant_settings is not provided
    """
    if not restaurant_settings:
        raise ValueError("restaurant_settings is required for multi-tenant delivery fee calculation")
    try:
        settings = restaurant_settings
        
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


def calculate_cart_totals(
    cart_items,
    delivery_type='delivery',
    delivery_fee=Decimal('0.00'),
    promo_code=None,
    user_reward=None,
    restaurant_settings=None,
):
    """
    Calculate complete cart totals including tax and delivery fees.
    
    Args:
        cart_items (list): List of cart items with price and quantity
        delivery_type (str): 'delivery' or 'pickup'
        delivery_fee (Decimal): Delivery fee amount (0 for pickup orders)
        promo_code (str): Promotional code for discount
        user_reward (UserReward): Selected UserReward object for discount calculation
        restaurant_settings (RestaurantSettings): REQUIRED - Business settings for multi-tenant support
        
    Returns:
        dict: Complete totals breakdown
    
    Raises:
        ValueError: If restaurant_settings is not provided
    """
    if not restaurant_settings:
        raise ValueError("restaurant_settings is required for multi-tenant cart totals calculation")
    vat_rate = restaurant_settings.vat_rate
    
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
    # Ensure final total meets minimum order requirement for this business
    if final_total < restaurant_settings.minimum_order:
        final_total = restaurant_settings.minimum_order
    
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
            restaurant_settings = order.restaurant_settings
            paystack = PaystackService(secret_key=restaurant_settings.paystack_secret_key)
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
