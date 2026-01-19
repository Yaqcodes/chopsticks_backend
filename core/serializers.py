from rest_framework import serializers
from .models import RestaurantSettings, Quote


class RestaurantSettingsSerializer(serializers.ModelSerializer):
    """Serializer for restaurant settings."""
    
    class Meta:
        model = RestaurantSettings
        fields = [
            'name', 'description', 'tagline', 'address', 'phone', 'email', 'website',
            'opening_hours', 'opening_time', 'closing_time', 'is_open',
            'delivery_radius', 'minimum_order', 'free_delivery_threshold',
            'vat_rate', 'pickup_delivery_fee', 'delivery_fee_base', 'delivery_fee_per_km',
            'accepts_cash', 'accepts_card', 'accepts_mobile_money',
            'facebook_url', 'instagram_url', 'twitter_url',
            'logo', 'favicon',
            'meta_title', 'meta_description', 'meta_keywords',
            'maintenance_mode', 'maintenance_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['maintenance_mode', 'maintenance_message', 'created_at', 'updated_at']


class PublicRestaurantSettingsSerializer(serializers.ModelSerializer):
    """Public serializer for restaurant settings (no sensitive info)."""
    
    class Meta:
        model = RestaurantSettings
        fields = [
            'name', 'description', 'tagline', 'address', 'phone', 'email', 'website',
            'opening_hours', 'opening_time', 'closing_time', 'is_open',
            'delivery_radius', 'minimum_order', 'free_delivery_threshold',
            'vat_rate', 'pickup_delivery_fee', 'delivery_fee_base', 'delivery_fee_per_km',
            'accepts_cash', 'accepts_card', 'accepts_mobile_money',
            'facebook_url', 'instagram_url', 'twitter_url',
            'logo', 'favicon'
        ]


class QuoteSerializer(serializers.ModelSerializer):
    """Serializer for quote requests (public submission)."""
    
    class Meta:
        model = Quote
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'message',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating quote requests (excludes admin fields)."""
    
    class Meta:
        model = Quote
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'message'
        ]
    
    def validate_first_name(self, value):
        """Validate first name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("First name must be at least 2 characters.")
        return value.strip()
    
    def validate_last_name(self, value):
        """Validate last name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Last name must be at least 2 characters.")
        return value.strip()
    
    def validate_message(self, value):
        """Validate message."""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters.")
        return value.strip()


class QuoteAdminSerializer(serializers.ModelSerializer):
    """Serializer for quote management in admin (includes admin notes)."""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Quote
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'message',
            'status', 'admin_notes', 'restaurant_settings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
