from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date
from .models import UserPoints, PointsTransaction, Reward, UserReward


def award_points_for_order(order):
    """Award points to user for completing an order."""
    
    if not order.user:
        return  # No points for guest orders
    
    try:
        user_points, created = UserPoints.objects.get_or_create(user=order.user)
        
        # Calculate base points (10 points per Naira)
        base_points = int(order.subtotal * settings.POINTS_PER_DOLLAR)
        
        # Check for first order bonus
        is_first_order = order.user.orders.count() == 1
        first_order_bonus = settings.FIRST_ORDER_BONUS_POINTS if is_first_order else 0
        
        # Check for birthday bonus
        is_birthday = False
        if order.user.date_of_birth:
            today = date.today()
            user_birthday = order.user.date_of_birth
            is_birthday = (today.month == user_birthday.month and today.day == user_birthday.day)
        
        birthday_bonus = settings.BIRTHDAY_BONUS_POINTS if is_birthday else 0
        
        # Calculate total points
        total_points = base_points + first_order_bonus + birthday_bonus
        
        # Award points
        reason_parts = [f"Order {order.order_number}"]
        if first_order_bonus > 0:
            reason_parts.append("First Order Bonus")
        if birthday_bonus > 0:
            reason_parts.append("Birthday Bonus")
        
        reason = " - ".join(reason_parts)
        user_points.add_points(total_points, reason)
        
        # Create transaction record with order reference
        PointsTransaction.objects.create(
            user=order.user,
            amount=total_points,
            transaction_type='earned',
            reason=reason,
            balance_after=user_points.balance,
            order=order
        )
        
        return total_points
    
    except Exception as e:
        # Log error but don't fail the order
        print(f"Error awarding points for order {order.order_number}: {str(e)}")
        return 0


def process_referral_bonus(user, referral_code):
    """Process referral bonus for a new user."""
    
    try:
        from accounts.models import User
        
        # Find the referring user
        referring_user = User.objects.get(referral_code=referral_code)
        
        # Check if this is the first order for the new user
        if user.orders.count() == 0:
            return False  # No orders yet
        
        # Check if referral bonus was already given
        existing_bonus = PointsTransaction.objects.filter(
            user=user,
            transaction_type='referral',
            reason__contains=referring_user.referral_code
        ).exists()
        
        if existing_bonus:
            return False  # Bonus already given
        
        # Award bonus to both users
        bonus_points = settings.REFERRAL_BONUS_POINTS
        
        # Award to new user
        user_points, created = UserPoints.objects.get_or_create(user=user)
        user_points.add_points(bonus_points, f"Referral Bonus from {referring_user.referral_code}")
        
        # Award to referring user
        referring_points, created = UserPoints.objects.get_or_create(user=referring_user)
        referring_points.add_points(bonus_points, f"Referral Bonus for {user.referral_code}")
        
        return True
    
    except User.DoesNotExist:
        return False
    except Exception as e:
        print(f"Error processing referral bonus: {str(e)}")
        return False


def check_reward_eligibility(user, reward):
    """Check if user is eligible for a specific reward."""
    
    try:
        user_points = user.points
        return user_points.balance >= reward.points_required
    except UserPoints.DoesNotExist:
        return False


def apply_reward_to_order(user_reward, order):
    """Apply a redeemed reward to an order."""
    
    reward = user_reward.reward
    
    if reward.reward_type == 'discount':
        if reward.discount_percentage:
            discount_amount = order.subtotal * (reward.discount_percentage / 100)
        else:
            discount_amount = reward.discount_amount
        
        order.discount_amount += discount_amount
        order.calculate_totals()
        order.save()
        
    elif reward.reward_type == 'free_delivery':
        order.delivery_fee = Decimal('0.00')
        order.calculate_totals()
        order.save()
    
    # Mark reward as used
    user_reward.use_reward(order)
    
    return True


def expire_old_rewards():
    """Expire rewards that have passed their expiration date."""
    
    expired_rewards = UserReward.objects.filter(
        status='active',
        expires_at__lt=timezone.now()
    )
    
    for user_reward in expired_rewards:
        user_reward.status = 'expired'
        user_reward.save()
    
    return expired_rewards.count()


def calculate_points_needed_for_reward(user, reward):
    """Calculate how many more points a user needs for a specific reward."""
    
    try:
        user_points = user.points
        points_needed = reward.points_required - user_points.balance
        return max(0, points_needed)
    except UserPoints.DoesNotExist:
        return reward.points_required


def get_user_loyalty_tier(user):
    """Get user's loyalty tier based on total points earned."""
    
    try:
        user_points = user.points
        total_earned = user_points.total_earned
        
        if total_earned >= settings.PLATINUM_TIER_POINTS:
            return 'platinum'
        elif total_earned >= settings.GOLD_TIER_POINTS:
            return 'gold'
        elif total_earned >= settings.SILVER_TIER_POINTS:
            return 'silver'
        else:
            return 'bronze'
    except UserPoints.DoesNotExist:
        return 'bronze'


def get_tier_benefits(tier):
    """Get benefits for a specific loyalty tier."""
    
    benefits = {
        'bronze': {
            'name': 'Bronze',
            'points_multiplier': 1.0,
            'free_delivery_threshold': 50.00,
            'special_offers': False
        },
        'silver': {
            'name': 'Silver',
            'points_multiplier': 1.1,
            'free_delivery_threshold': 30.00,
            'special_offers': True
        },
        'gold': {
            'name': 'Gold',
            'points_multiplier': 1.2,
            'free_delivery_threshold': 20.00,
            'special_offers': True
        },
        'platinum': {
            'name': 'Platinum',
            'points_multiplier': 1.5,
            'free_delivery_threshold': 0.00,
            'special_offers': True
        }
    }
    
    return benefits.get(tier, benefits['bronze'])


def award_points_for_physical_visit(user, visit_amount=None):
    """Award points to user for physical visit via QR code scan."""
    
    if not user:
        return 0
    
    try:
        user_points, created = UserPoints.objects.get_or_create(user=user)
        
        # Base points for physical visit (can be configured)
        base_points = getattr(settings, 'PHYSICAL_VISIT_POINTS', 500)
        
        # Additional points based on visit amount if provided
        amount_points = 0
        if visit_amount:
            amount_points = int(visit_amount * settings.POINTS_PER_DOLLAR)
        
        # Calculate total points
        total_points = base_points + amount_points
        
        # Award points
        reason_parts = ["Physical Visit"]
        if visit_amount:
            reason_parts.append(f"Amount: ₦{visit_amount}")
        
        reason = " - ".join(reason_parts)
        user_points.add_points(total_points, reason)
        
        # Create transaction record
        PointsTransaction.objects.create(
            user=user,
            amount=total_points,
            transaction_type='physical_visit',
            reason=reason,
            balance_after=user_points.balance
        )
        
        return total_points
    
    except Exception as e:
        # Log error but don't fail the scan
        print(f"Error awarding points for physical visit for user {user.email}: {str(e)}")
        return 0


def scan_loyalty_card(qr_code, visit_amount=None):
    """Scan a loyalty card QR code and award points."""
    
    try:
        from .models import LoyaltyCard
        
        # Find the loyalty card by QR code
        loyalty_card = LoyaltyCard.objects.get(qr_code=qr_code, is_active=True)
        
        # Check if card was recently scanned (prevent abuse)
        from django.utils import timezone
        from datetime import timedelta
        
        if loyalty_card.last_scan:
            time_since_last_scan = timezone.now() - loyalty_card.last_scan
            min_scan_interval = getattr(settings, 'MIN_SCAN_INTERVAL_MINUTES', 30)
            
            if time_since_last_scan < timedelta(minutes=min_scan_interval):
                return {
                    'success': False,
                    'error': f'Card was scanned recently. Please wait {min_scan_interval} minutes between scans.'
                }
        
        # Award points
        points_awarded = award_points_for_physical_visit(
            loyalty_card.user, 
            visit_amount
        )
        
        # Mark card as scanned
        loyalty_card.scan_card()
        
        return {
            'success': True,
            'user': loyalty_card.user.email,
            'points_awarded': points_awarded,
            'new_balance': loyalty_card.user.points.balance,
            'scan_time': loyalty_card.last_scan
        }
    
    except LoyaltyCard.DoesNotExist:
        return {
            'success': False,
            'error': 'Invalid or inactive loyalty card QR code.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error scanning loyalty card: {str(e)}'
        }
