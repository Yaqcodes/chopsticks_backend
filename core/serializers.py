from rest_framework import serializers
from .models import RestaurantSettings


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
