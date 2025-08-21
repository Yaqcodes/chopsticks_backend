from rest_framework import serializers
from .models import PromoCode, PromoCodeUsage


class PromoCodeSerializer(serializers.ModelSerializer):
    """Serializer for promotional codes."""
    
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_type_display',
            'discount_value', 'minimum_order_amount', 'maximum_discount',
            'is_active', 'usage_limit', 'current_usage', 'is_valid',
            'valid_from', 'valid_until', 'created_at'
        ]
        read_only_fields = ['id', 'current_usage', 'is_valid', 'created_at']


class PromoCodeValidationSerializer(serializers.Serializer):
    """Serializer for promo code validation."""
    
    code = serializers.CharField(max_length=20)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_code(self, value):
        """Validate that the promo code exists and is valid."""
        try:
            promo_code = PromoCode.objects.get(code=value.upper())
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError("Invalid promotional code.")
        
        if not promo_code.is_valid:
            raise serializers.ValidationError("This promotional code is not currently valid.")
        
        return value
    
    def validate(self, attrs):
        """Validate promo code for the specific order and user."""
        code = attrs['code']
        order_amount = attrs['order_amount']
        user = self.context['request'].user
        
        try:
            promo_code = PromoCode.objects.get(code=code.upper())
            
            # Check if valid for user
            if not promo_code.is_valid_for_user(user):
                raise serializers.ValidationError("This promotional code is not valid for you.")
            
            # Check minimum order amount
            if order_amount < promo_code.minimum_order_amount:
                raise serializers.ValidationError(
                    f"Minimum order amount of ${promo_code.minimum_order_amount} required for this code."
                )
            
            # Calculate discount
            discount_amount = promo_code.calculate_discount(order_amount)
            
            attrs['promo_code'] = promo_code
            attrs['discount_amount'] = discount_amount
            
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError("Invalid promotional code.")
        
        return attrs


class PromoCodeUsageSerializer(serializers.ModelSerializer):
    """Serializer for promo code usage tracking."""
    
    promo_code_code = serializers.CharField(source='promo_code.code', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = PromoCodeUsage
        fields = [
            'id', 'promo_code', 'promo_code_code', 'user', 'user_email',
            'order', 'order_number', 'discount_amount', 'used_at'
        ]
        read_only_fields = [
            'id', 'promo_code_code', 'user_email', 'order_number', 'used_at'
        ]


class ActivePromotionsSerializer(serializers.ModelSerializer):
    """Serializer for active promotional codes."""
    
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    
    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_type_display',
            'discount_value', 'minimum_order_amount', 'maximum_discount',
            'valid_until'
        ]
