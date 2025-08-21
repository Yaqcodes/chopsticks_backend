from rest_framework import serializers
from .models import UserPoints, PointsTransaction, Reward, UserReward, LoyaltyCard


class UserPointsSerializer(serializers.ModelSerializer):
    """Serializer for user points balance."""
    
    class Meta:
        model = UserPoints
        fields = ['balance', 'total_earned', 'total_spent', 'created_at', 'updated_at']
        read_only_fields = ['balance', 'total_earned', 'total_spent', 'created_at', 'updated_at']


class PointsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for points transaction history."""
    
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'amount', 'transaction_type', 'transaction_type_display',
            'reason', 'balance_after', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'amount', 'transaction_type', 'reason', 'balance_after', 'order', 'created_at']


class RewardSerializer(serializers.ModelSerializer):
    """Serializer for available rewards."""
    
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    can_redeem = serializers.SerializerMethodField()
    
    class Meta:
        model = Reward
        fields = [
            'id', 'name', 'description', 'reward_type', 'reward_type_display',
            'points_required', 'discount_percentage', 'discount_amount',
            'free_item', 'is_active', 'is_available', 'can_redeem',
            'valid_from', 'valid_until'
        ]
        read_only_fields = ['id', 'is_available', 'can_redeem']
    
    def get_can_redeem(self, obj):
        """Check if current user can redeem this reward."""
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.can_be_redeemed_by(user)
        return False


class UserRewardSerializer(serializers.ModelSerializer):
    """Serializer for user redeemed rewards."""
    
    reward_name = serializers.CharField(source='reward.name', read_only=True)
    reward_description = serializers.CharField(source='reward.description', read_only=True)
    reward_type = serializers.CharField(source='reward.reward_type', read_only=True)
    discount_percentage = serializers.DecimalField(source='reward.discount_percentage', max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    discount_amount = serializers.DecimalField(source='reward.discount_amount', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    free_item = serializers.IntegerField(source='reward.free_item.id', read_only=True, allow_null=True)
    free_item_price = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    def get_free_item_price(self, obj):
        """Safely get free item price, handling None cases."""
        if obj.reward.free_item:
            return obj.reward.free_item.price
        return None
    
    class Meta:
        model = UserReward
        fields = [
            'id', 'reward', 'reward_name', 'reward_description', 'reward_type',
            'discount_percentage', 'discount_amount', 'free_item', 'free_item_price',
            'points_spent', 'status', 'status_display', 'redeemed_at',
            'used_at', 'expires_at', 'order'
        ]
        read_only_fields = [
            'id', 'reward_name', 'reward_description', 'reward_type',
            'discount_percentage', 'discount_amount', 'free_item', 'free_item_price',
            'status', 'redeemed_at', 'used_at', 'expires_at', 'order'
        ]


class RewardRedemptionSerializer(serializers.Serializer):
    """Serializer for reward redemption."""
    
    reward_id = serializers.IntegerField()
    
    def validate_reward_id(self, value):
        """Validate that the reward exists and can be redeemed."""
        try:
            reward = Reward.objects.get(id=value)
        except Reward.DoesNotExist:
            raise serializers.ValidationError("Reward not found.")
        
        if not reward.is_available:
            raise serializers.ValidationError("Reward is not available for redemption.")
        
        user = self.context['request'].user
        if not reward.can_be_redeemed_by(user):
            raise serializers.ValidationError("Insufficient points to redeem this reward.")
        
        return value


class PointsEarningSerializer(serializers.Serializer):
    """Serializer for points earning calculation."""
    
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_first_order = serializers.BooleanField(default=False)
    is_birthday = serializers.BooleanField(default=False)
    
    def calculate_points(self):
        """Calculate points to be awarded."""
        from django.conf import settings
        
        order_amount = self.validated_data['order_amount']
        is_first_order = self.validated_data['is_first_order']
        is_birthday = self.validated_data['is_birthday']
        
        # Base points (10 points per Naira)
        base_points = int(order_amount * settings.POINTS_PER_DOLLAR)
        
        # Bonus points
        bonus_points = 0
        if is_first_order:
            bonus_points += settings.FIRST_ORDER_BONUS_POINTS
        if is_birthday:
            bonus_points += settings.BIRTHDAY_BONUS_POINTS
        
        total_points = base_points + bonus_points
        
        return {
            'base_points': base_points,
            'bonus_points': bonus_points,
            'total_points': total_points
        }


class ReferralBonusSerializer(serializers.Serializer):
    """Serializer for referral bonus."""
    
    referral_code = serializers.CharField(max_length=8)
    
    def validate_referral_code(self, value):
        """Validate referral code."""
        from accounts.models import User
        
        try:
            user = User.objects.get(referral_code=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid referral code.")
        
        current_user = self.context['request'].user
        if user == current_user:
            raise serializers.ValidationError("You cannot refer yourself.")
        
        return value


class LoyaltyCardSerializer(serializers.ModelSerializer):
    """Serializer for loyalty card model."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    loyalty_tier = serializers.SerializerMethodField()
    tier_benefits = serializers.SerializerMethodField()
    points_balance = serializers.SerializerMethodField()
    points_total_earned = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyCard
        fields = [
            'id', 'qr_code', 'is_active', 'created_at', 'last_scan', 
            'user_email', 'user_name', 'loyalty_tier', 'tier_benefits',
            'points_balance', 'points_total_earned'
        ]
        read_only_fields = ['qr_code', 'created_at', 'last_scan']
    
    def get_loyalty_tier(self, obj):
        """Get user's loyalty tier."""
        from .services import get_user_loyalty_tier
        return get_user_loyalty_tier(obj.user)
    
    def get_tier_benefits(self, obj):
        """Get benefits for user's loyalty tier."""
        from .services import get_user_loyalty_tier, get_tier_benefits
        tier = get_user_loyalty_tier(obj.user)
        return get_tier_benefits(tier)
    
    def get_points_balance(self, obj):
        """Get user's current points balance."""
        try:
            return obj.user.points.balance
        except:
            return 0
    
    def get_points_total_earned(self, obj):
        """Get user's total points earned."""
        try:
            return obj.user.points.total_earned
        except:
            return 0


class QRCodeScanSerializer(serializers.Serializer):
    """Serializer for QR code scanning."""
    
    qr_code = serializers.CharField(max_length=255)
    visit_amount = serializers.IntegerField(required=False, allow_null=True)
    visit_type = serializers.ChoiceField(
        choices=[
            ('general', 'General Visit'),
            ('lunch', 'Lunch'),
            ('dinner', 'Dinner'),
            ('happy_hour', 'Happy Hour'),
        ],
        default='general'
    )


class QRCodeScanResponseSerializer(serializers.Serializer):
    """Serializer for QR code scan response."""
    
    success = serializers.BooleanField()
    user = serializers.EmailField(required=False)
    points_awarded = serializers.IntegerField(required=False)
    new_balance = serializers.IntegerField(required=False)
    scan_time = serializers.DateTimeField(required=False)
    error = serializers.CharField(required=False)
