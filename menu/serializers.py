from django.conf import settings
from rest_framework import serializers
from .models import Category, MenuItem


def _media_url(path):
    """Return URL path for media file (e.g. /media/menu_items/2.jpeg). Frontend can then resolve to absolute URL."""
    if not path or not str(path).strip():
        return None
    path = str(path).lstrip('/')
    base = (settings.MEDIA_URL or '/media/').rstrip('/')
    return f"{base}/{path}" if path else None


def _normalize_colors(colors):
    """Return list of { name, hex } for frontend. Name defaults to hex when empty."""
    if not colors or not isinstance(colors, list):
        return []
    out = []
    for c in colors:
        if not isinstance(c, dict):
            continue
        hex_val = (c.get('hex') or '#000000').strip()
        if not hex_val.startswith('#'):
            hex_val = '#' + hex_val
        name = (c.get('name') or '').strip() or hex_val
        out.append({'name': name, 'hex': hex_val})
    return out


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for menu categories."""
    
    menu_items_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image', 'is_active', 'sort_order', 'menu_items_count']
    
    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_menu_items_count(self, obj):
        """Get count of available menu items in category."""
        return obj.menu_items.filter(is_available=True).count()


class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for menu items."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    badges_display = serializers.SerializerMethodField()
    formatted_price = serializers.CharField(read_only=True)
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'size', 'sizes', 'sku', 'price', 'formatted_price',
            'category', 'category_name', 'category_id', 'image',
            'badges', 'badges_display', 'allergens', 'nutritional_info',
            'is_available', 'is_featured', 'preparation_time', 'sort_order',
            'gender', 'colors',
        ]

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))
    
    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        """Return size string: model size if set, else comma-joined sizes (ZMall apparel)."""
        if obj.size and str(obj.size).strip():
            return obj.size
        if getattr(obj, 'sizes', None):
            return ', '.join(str(s) for s in obj.sizes)
        return ''
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()


class MenuItemDetailSerializer(MenuItemSerializer):
    """Detailed serializer for menu items with full information."""
    
    images = serializers.SerializerMethodField()
    
    class Meta(MenuItemSerializer.Meta):
        fields = MenuItemSerializer.Meta.fields + ['images', 'created_at', 'updated_at']
    
    def get_images(self, obj):
        """Primary image first, then extra_images, all as media URLs."""
        urls = []
        if obj.image:
            urls.append(_media_url(obj.image))
        extra_qs = getattr(obj, 'extra_images', None)
        if extra_qs is not None:
            for extra in extra_qs.order_by('sort_order', 'id'):
                if getattr(extra, 'image', None):
                    urls.append(_media_url(extra.image))
        return urls


class FeaturedItemsSerializer(serializers.ModelSerializer):
    """Serializer for featured menu items."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    badges_display = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'size', 'sizes', 'sku', 'price', 'formatted_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'preparation_time', 'gender', 'colors',
        ]

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))

    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        if obj.size and str(obj.size).strip():
            return obj.size
        if getattr(obj, 'sizes', None):
            return ', '.join(str(s) for s in obj.sizes)
        return ''
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()


class MenuSearchSerializer(serializers.ModelSerializer):
    """Serializer for menu search results."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    badges_display = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'size', 'sizes', 'sku', 'price', 'formatted_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'is_featured', 'gender', 'colors',
        ]

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))

    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        if obj.size and str(obj.size).strip():
            return obj.size
        if getattr(obj, 'sizes', None):
            return ', '.join(str(s) for s in obj.sizes)
        return ''
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()
