from rest_framework import serializers
from django.utils.text import slugify

from core.media_urls import absolute_media_url

from .models import Category, MenuItem, Product
from .size_grids import get_size_grid_values, merge_display_sizes
from .size_sort import size_sort_key


# Back-compat alias: callers in storefront/services.py still import _media_url from
# this module. The single implementation lives in core.media_urls.
_media_url = absolute_media_url


def _category_storefront_name(category):
    if not category:
        return ''
    return category.get_storefront_name()


class CategoryStorefrontNameMixin:
    """Expose category label using optional display_name."""

    category_name = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return _category_storefront_name(getattr(obj, 'category', None))


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


def _iter_product_variants_for_facets(product):
    """Prefer prefetched variants; otherwise a cheap values queryset is not used — keep .only()."""
    cache = getattr(product, '_prefetched_objects_cache', {})
    if 'variants' in cache:
        return cache['variants']
    return product.variants.only('size', 'colors')


def _distinct_variant_sizes(product):
    seen_lower = set()
    ordered = []
    for v in _iter_product_variants_for_facets(product):
        sz = getattr(v, 'size', None)
        if sz is not None and str(sz).strip():
            s = str(sz).strip()
            k = s.lower()
            if k not in seen_lower:
                seen_lower.add(k)
                ordered.append(s)
    return sorted(ordered, key=size_sort_key)


def _distinct_variant_colors(product):
    by_key = {}
    for v in _iter_product_variants_for_facets(product):
        for c in _normalize_colors(getattr(v, 'colors', None)):
            key = str(c.get('name', '')).strip().lower()
            if key and key not in by_key:
                by_key[key] = {'name': c['name'], 'hex': c['hex']}
    return sorted(by_key.values(), key=lambda x: str(x.get('name', '')).lower())


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for menu categories."""

    menu_items_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'display_name',
            'label',
            'slug',
            'description',
            'image',
            'show_in_men',
            'show_in_women',
            'show_in_unisex',
            'size_grid',
            'is_active',
            'sort_order',
            'menu_items_count',
        ]

    def get_label(self, obj):
        return obj.get_storefront_name()
    
    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_menu_items_count(self, obj):
        """Get count of available menu items in category."""
        return obj.menu_items.filter(is_available=True).count()


class MenuItemSerializer(CategoryStorefrontNameMixin, serializers.ModelSerializer):
    """Serializer for menu items."""

    category_id = serializers.IntegerField(source='category.id', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True, allow_null=True)
    badges_display = serializers.SerializerMethodField()
    formatted_price = serializers.CharField(read_only=True)
    effective_price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'product_id', 'name', 'description', 'size', 'sizes', 'sku', 'barcode', 'price', 'formatted_price',
            'on_sale', 'sale_price', 'effective_price',
            'category', 'category_name', 'category_id', 'category_slug', 'image',
            'badges', 'badges_display', 'allergens', 'nutritional_info',
            'is_available', 'is_featured', 'preparation_time', 'sort_order',
            'gender', 'colors',
        ]

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))
    
    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        """Return ``MenuItem.size`` only (one size per SKU row)."""
        if obj.size and str(obj.size).strip():
            return obj.size
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


class FeaturedItemsSerializer(CategoryStorefrontNameMixin, serializers.ModelSerializer):
    """Serializer for featured menu items."""

    formatted_price = serializers.CharField(read_only=True)
    effective_price = serializers.SerializerMethodField()
    badges_display = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'product_id', 'name', 'description', 'size', 'sizes', 'sku', 'barcode', 'price', 'formatted_price',
            'on_sale', 'sale_price', 'effective_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'preparation_time', 'gender', 'colors',
        ]

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))

    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        if obj.size and str(obj.size).strip():
            return obj.size
        return ''
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()


class MenuSearchSerializer(CategoryStorefrontNameMixin, serializers.ModelSerializer):
    """Serializer for menu search results."""

    formatted_price = serializers.CharField(read_only=True)
    effective_price = serializers.SerializerMethodField()
    badges_display = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'product_id', 'name', 'description', 'size', 'sizes', 'sku', 'barcode', 'price', 'formatted_price',
            'on_sale', 'sale_price', 'effective_price',
            'category_name', 'image', 'badges', 'badges_display',
            'is_available', 'is_featured', 'gender', 'colors',
        ]

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_colors(self, obj):
        return _normalize_colors(getattr(obj, 'colors', None))

    def get_image(self, obj):
        return _media_url(obj.image) if obj.image else None
    
    def get_size(self, obj):
        if obj.size and str(obj.size).strip():
            return obj.size
        return ''
    
    def get_badges_display(self, obj):
        """Get badge display names."""
        return obj.get_badges_display()

class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'name',
            'display_name',
            'description',
            'image',
            'show_in_men',
            'show_in_women',
            'show_in_unisex',
            'is_active',
            'sort_order',
        ]

    def create(self, validated_data):
        # slug is auto-generated like in ZmallCategoryAdmin.save_model
        from django.utils.text import slugify
        restaurant_settings = self.context['restaurant_settings']
        obj = Category(**validated_data, restaurant_settings=restaurant_settings)
        base = slugify(obj.name)[:100] or 'category'
        candidate = base
        n = 0
        while Category.objects.filter(restaurant_settings=restaurant_settings, slug=candidate).exists():
            n += 1
            suffix = f'-{n}'
            candidate = f'{base[:100 - len(suffix)]}{suffix}'
        obj.slug = candidate
        obj.save()
        return obj


class MenuItemWriteSerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'size', 'sizes', 'sku', 'barcode',
            'price', 'on_sale', 'sale_price', 'effective_price', 'category', 'product', 'image', 'badges', 'allergens',
            'nutritional_info', 'is_available', 'is_featured',
            'preparation_time', 'sort_order', 'gender', 'colors',
        ]
        extra_kwargs = {
            'product': {'required': False, 'allow_null': True},
        }

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def validate_category(self, value):
        # Ensure the category belongs to the same business
        restaurant_settings = self.context['restaurant_settings']
        if value.restaurant_settings != restaurant_settings:
            raise serializers.ValidationError("Category does not belong to this business.")
        return value

    def validate_product(self, value):
        if value is None:
            return value
        restaurant_settings = self.context['restaurant_settings']
        if value.restaurant_settings != restaurant_settings:
            raise serializers.ValidationError('Catalog Product does not belong to this business.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        on_sale = attrs.get('on_sale', getattr(instance, 'on_sale', False) if instance else False)
        sale_price = attrs.get('sale_price', getattr(instance, 'sale_price', None) if instance else None)
        price = attrs.get('price', getattr(instance, 'price', None) if instance else None)
        if on_sale:
            if sale_price is None:
                raise serializers.ValidationError({'sale_price': 'Sale price is required when on sale.'})
            if price is not None and sale_price >= price:
                raise serializers.ValidationError({'sale_price': 'Sale price must be less than list price.'})
        return attrs


class ProductVariantSerializer(serializers.ModelSerializer):
    """One linked MenuItem (SKU); ``is_available`` is storefront purchaseable."""

    effective_price = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id',
            'barcode',
            'size',
            'color',
            'price',
            'on_sale',
            'sale_price',
            'effective_price',
            'sku',
            'is_available',
            'image',
            'images',
        ]

    def get_effective_price(self, obj):
        return obj.get_effective_price()

    def get_color(self, obj):
        norm = _normalize_colors(getattr(obj, 'colors', None))
        return norm[0] if norm else None

    def get_is_available(self, obj):
        from .product_catalog import variant_is_purchasable

        return variant_is_purchasable(obj)

    def _menuitem_image_url(self, filefield):
        """Resolve ImageField/FileField to a media URL path (handles FieldFile edge cases)."""
        if not filefield:
            return None
        name = getattr(filefield, 'name', None)
        if name:
            return _media_url(name)
        s = str(filefield).strip()
        return _media_url(s) if s else None

    def get_image(self, obj):
        return self._menuitem_image_url(getattr(obj, 'image', None))

    def get_images(self, obj):
        urls = []
        primary = self._menuitem_image_url(getattr(obj, 'image', None))
        if primary:
            urls.append(primary)
        extras = getattr(obj, 'extra_images', None)
        if extras is not None:
            for ex in extras.all().order_by('sort_order', 'id'):
                u = self._menuitem_image_url(getattr(ex, 'image', None))
                if u and u not in urls:
                    urls.append(u)
        return urls


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    category_id = serializers.IntegerField(source='category.id', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True, allow_null=True)
    category_size_grid = serializers.CharField(source='category.size_grid', read_only=True)
    image = serializers.SerializerMethodField()
    badges_display = serializers.SerializerMethodField()
    variant_count = serializers.IntegerField(read_only=True)
    min_variant_price = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'description',
            'category_id',
            'category_name',
            'category_slug',
            'category_size_grid',
            'gender',
            'base_price',
            'min_variant_price',
            'is_available',
            'is_featured',
            'badges',
            'badges_display',
            'sort_order',
            'image',
            'variant_count',
            'sizes',
            'colors',
            'variants',
        ]

    def get_category_name(self, obj):
        return _category_storefront_name(getattr(obj, 'category', None))

    def get_image(self, obj):
        gi = getattr(obj, 'gallery_images', None)
        if gi is None:
            return None
        first = gi.order_by('sort_order', 'id').first()
        return _media_url(first.image) if first and first.image else None

    def get_badges_display(self, obj):
        return obj.get_badges_display()

    def get_min_variant_price(self, obj):
        v = getattr(obj, '_min_variant_price', None)
        return v if v is not None else obj.base_price

    def get_sizes(self, obj):
        fac = getattr(obj, '_list_facet_sizes', None)
        if fac is not None:
            return fac
        variant_sizes = _distinct_variant_sizes(obj)
        category = getattr(obj, 'category', None)
        if category:
            fixed = get_size_grid_values(getattr(category, 'size_grid', None))
            if fixed:
                return merge_display_sizes(fixed, variant_sizes)
        return variant_sizes

    def get_colors(self, obj):
        fac = getattr(obj, '_list_facet_colors', None)
        if fac is not None:
            return fac
        return _distinct_variant_colors(obj)

    def get_variants(self, obj):
        return getattr(obj, '_list_variant_cards', None) or []


class ProductDetailSerializer(ProductListSerializer):
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'images',
            'meta_title',
            'meta_description',
            'created_at',
            'updated_at',
        ]

    def get_images(self, obj):
        gi = getattr(obj, 'gallery_images', None)
        if gi is None:
            return []
        return [
            _media_url(g.image) for g in gi.order_by('sort_order', 'id') if g.image
        ]

    def get_variants(self, obj):
        qs = getattr(obj, 'variants', None)
        if qs is None:
            return []
        ordered = qs.all().order_by('size', 'id')
        return ProductVariantSerializer(ordered, many=True).data


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'category',
            'gender',
            'base_price',
            'badges',
            'is_available',
            'is_featured',
            'sort_order',
            'meta_title',
            'meta_description',
        ]

    def validate_category(self, value):
        rs = self.context['restaurant_settings']
        if value.restaurant_settings != rs:
            raise serializers.ValidationError('Category does not belong to this business.')
        return value

    def validate_badges(self, value):
        allowed = {c[0] for c in Product.BADGE_CHOICES_ZMALL}
        if not value:
            return []
        unknown = [b for b in value if b not in allowed]
        if unknown:
            raise serializers.ValidationError('Invalid badge values.')
        return value

    def create(self, validated_data):
        rs = self.context['restaurant_settings']
        obj = Product(restaurant_settings=rs, **validated_data)
        base = slugify(obj.name)[:100] or 'product'
        candidate = base
        n = 0
        while Product.objects.filter(restaurant_settings=rs, slug=candidate).exists():
            n += 1
            suffix = f'-{n}'
            candidate = f'{base[:100 - len(suffix)]}{suffix}'
        obj.slug = candidate
        obj.save()
        return obj
