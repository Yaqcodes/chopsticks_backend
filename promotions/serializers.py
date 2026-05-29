from rest_framework import serializers
from .models import PromoCode, PromoCodeUsage
from .services import PromoCodeError, normalize_promo_code, validate_promo_for_checkout


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
    guest_email = serializers.EmailField(required=False, allow_blank=True)
    
    def validate_code(self, value):
        return normalize_promo_code(value) or value
    
    def validate(self, attrs):
        """Validate promo code for the specific order and customer (business-scoped)."""
        from core.utils import get_business_from_request
        
        code = attrs['code']
        order_amount = attrs['order_amount']
        request = self.context['request']
        user = request.user
        guest_email = attrs.get('guest_email') or None
        
        try:
            restaurant_settings = get_business_from_request(request)
            promo_code, discount_amount = validate_promo_for_checkout(
                code,
                order_amount,
                restaurant_settings,
                user=user if user.is_authenticated else None,
                guest_email=guest_email,
            )
            attrs['promo_code'] = promo_code
            attrs['discount_amount'] = discount_amount
        except PromoCodeError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        except ValueError as exc:
            raise serializers.ValidationError(f'Business identification failed: {exc}') from exc
        
        return attrs


class PromoCodeUsageSerializer(serializers.ModelSerializer):
    """Serializer for promo code usage tracking."""
    
    promo_code_code = serializers.CharField(source='promo_code.code', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = PromoCodeUsage
        fields = [
            'id', 'promo_code', 'promo_code_code', 'user', 'user_email', 'guest_email',
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
