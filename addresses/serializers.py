from rest_framework import serializers
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for address CRUD operations."""
    
    full_address = serializers.CharField(read_only=True)
    coordinates = serializers.SerializerMethodField()
    postal_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Address
        fields = [
            'id', 'full_name', 'phone', 'address', 'city', 'state', 
            'postal_code', 'country', 'latitude', 'longitude', 
            'is_default', 'address_type', 'full_address', 'coordinates',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_coordinates(self, obj):
        """Get coordinates as tuple."""
        return obj.coordinates
    
    def validate(self, attrs):
        """Validate address data."""
        # Ensure at least one address is default if this is the user's first address
        user = self.context['request'].user
        if not user.addresses.exists() and not attrs.get('is_default'):
            attrs['is_default'] = True
        
        return attrs


class AddressCreateSerializer(AddressSerializer):
    """Serializer for creating new addresses."""
    
    class Meta(AddressSerializer.Meta):
        fields = AddressSerializer.Meta.fields[:-2]  # Exclude created_at, updated_at


class AddressUpdateSerializer(AddressSerializer):
    """Serializer for updating addresses."""
    
    class Meta(AddressSerializer.Meta):
        fields = AddressSerializer.Meta.fields[:-2]  # Exclude created_at, updated_at


class GeocodeRequestSerializer(serializers.Serializer):
    """Serializer for geocoding requests."""
    
    address = serializers.CharField()
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    country = serializers.CharField(default='Nigeria')


class GeocodeResponseSerializer(serializers.Serializer):
    """Serializer for geocoding responses."""
    
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    formatted_address = serializers.CharField()
    confidence = serializers.FloatField(required=False)
