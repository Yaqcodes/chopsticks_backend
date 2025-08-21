from rest_framework import serializers
from .models import Category, MenuItem


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for menu categories."""
    
    menu_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image', 'is_active', 'sort_order', 'menu_items_count']
    
    def get_menu_items_count(self, obj):
        """Get count of available menu items in category."""
        return obj.menu_items.filter(is_available=True).count()


class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for menu items."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    badges_display = serializers.SerializerMethodField()
    formatted_price = serializers.CharField(read_only=True)
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'formatted_price',
            'category', 'category_name', 'category_id', 'image',
            'badges', 'badges_display', 'allergens', 'nutritional_info',
            'is_available', 'is_featured', 'preparation_time', 'sort_order'
        ]
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()


class MenuItemDetailSerializer(MenuItemSerializer):
    """Detailed serializer for menu items with full information."""
    
    class Meta(MenuItemSerializer.Meta):
        fields = MenuItemSerializer.Meta.fields + ['created_at', 'updated_at']


class FeaturedItemsSerializer(serializers.ModelSerializer):
    """Serializer for featured menu items."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    badges_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'formatted_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'preparation_time'
        ]
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()


class MenuSearchSerializer(serializers.ModelSerializer):
    """Serializer for menu search results."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    badges_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'formatted_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'is_featured'
        ]
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()
