from django import forms
from django.contrib import admin
from django.db import connection
from django.db.models import Max
from django.utils.html import format_html
from django.utils.text import slugify
from unfold.admin import ModelAdmin
from .models import Category, MenuItem, MenuItemImage
from core.admin_sites import roschi_admin_site, chopsticks_admin_site, zmall_admin_site
from core.main_admin_site import main_admin_site


class ZmallBadgeListFilter(admin.SimpleListFilter):
    """Readable badge filter: Bestseller, Sale, or None (no permutations)."""
    title = 'By badge'
    parameter_name = 'badge'

    def lookups(self, request, model_admin):
        return [
            ('bestseller', 'Bestseller'),
            ('sale', 'Sale'),
            ('none', 'None'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        if value == 'none':
            return queryset.filter(badges=[])
        # Single-badge filter (DB-agnostic for JSONField)
        if connection.vendor == 'sqlite':
            return queryset.filter(badges__icontains=f'"{value}"')
        return queryset.filter(badges__contains=[value])


class ZmallCategoryListFilter(admin.SimpleListFilter):
    """Category filter limited to ZMall categories (same business as the admin site)."""
    title = 'category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        if not hasattr(model_admin.admin_site, 'get_business_settings'):
            return []
        business_settings = model_admin.admin_site.get_business_settings()
        if not business_settings:
            return []
        categories = Category.objects.filter(restaurant_settings=business_settings).order_by('sort_order', 'name')
        return [(c.pk, str(c.name)) for c in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category_id=self.value())
        return queryset


class BusinessAdminMixin:
    """
    Mixin to add permission methods for business admin classes.
    
    Ensures that staff users linked to the business can view and manage models.
    """
    
    def has_module_permission(self, request):
        """Check if user can view this app in admin."""
        # Delegate to admin site's permission check
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        # Fallback for default admin site
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """Check if user can view this model."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Check if user can add objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """Check if user can change objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Check if user can delete objects."""
        if hasattr(self.admin_site, 'has_permission'):
            return self.admin_site.has_permission(request)
        return request.user.is_staff


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    
    list_display = ['name', 'slug', 'is_active', 'sort_order', 'menu_items_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'image', 'is_active', 'sort_order', 'restaurant_settings')}),
    )
    
    def menu_items_count(self, obj):
        """Display count of menu items in category."""
        return obj.menu_items.count()
    menu_items_count.short_description = 'Menu Items'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('restaurant_settings')


class MenuItemForm(forms.ModelForm):
    """Form for MenuItem; image required on add, optional on edit."""
    class Meta:
        model = MenuItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].required = False


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for MenuItem model."""
    form = MenuItemForm
    list_display = ['name', 'category', 'size', 'sku', 'barcode', 'restaurant_settings', 'price', 'is_available', 'is_featured', 'sort_order']
    list_filter = ['restaurant_settings', 'category', 'is_available', 'is_featured', 'badges', 'created_at']
    search_fields = ['name', 'description', 'size', 'category__name', 'barcode']
    ordering = ['category', 'sort_order', 'name']
    list_editable = ['is_available', 'is_featured', 'sort_order']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'size', 'sku', 'barcode', 'category', 'restaurant_settings', 'price', 'image')
        }),
        ('Status & Display', {
            'fields': ('is_available', 'is_featured', 'sort_order', 'preparation_time')
        }),
        ('Additional Information', {
            'fields': ('badges', 'allergens', 'nutritional_info'),
            'classes': ('collapse',)
        }),
        ('Apparel (optional)', {
            'fields': ('gender', 'sizes', 'colors', 'images'),
            'classes': ('collapse',),
            'description': 'Used by ZMall; leave blank for food/beverage.',
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('category', 'restaurant_settings')


# Roschi Water Admin Classes
class RoschiCategoryAdmin(BusinessAdminMixin, ModelAdmin):
    """Product categories - Organize your products into groups like 'Bottled Water' or 'Sachet Water'."""
    
    list_display = ['name', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    list_editable = ['is_active']
    
    def product_count(self, obj):
        """How many products are in this category."""
        business_settings = self._get_business_settings()
        if business_settings:
            return obj.menu_items.filter(restaurant_settings=business_settings).count()
        return 0
    product_count.short_description = 'Number of Products'
    
    def get_queryset(self, request):
        """Show only categories for this business."""
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        """Automatically link category to this business."""
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class RoschiMenuItemAdmin(BusinessAdminMixin, ModelAdmin):
    """Products - Manage your water products that customers can order."""
    form = MenuItemForm
    list_display = ['name', 'category', 'size', 'sku', 'price_display', 'is_available', 'stock_status']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description', 'size', 'category__name']
    ordering = ['category', 'name']
    list_editable = ['is_available', 'sku']
    
    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'description', 'category', 'size', 'price', 'image'),
            'description': 'What customers will see when browsing your products'
        }),
        ('Stock Management', {
            'fields': ('sku', 'is_available'),
            'description': 'How many units you have in stock and whether customers can order this product'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Add user-friendly help text to form fields."""
        form = super().get_form(request, obj, **kwargs)
        
        # Update field labels and help text
        if 'name' in form.base_fields:
            form.base_fields['name'].label = 'Product Name'
            form.base_fields['name'].help_text = 'The name customers will see (e.g., "ROSCHI Bottled Water")'
        
        if 'description' in form.base_fields:
            form.base_fields['description'].label = 'Product Description'
            form.base_fields['description'].help_text = 'Describe your product to customers'
        
        if 'size' in form.base_fields:
            form.base_fields['size'].label = 'Size or Pack'
            form.base_fields['size'].help_text = 'Product size or pack information (e.g., "24-pack 35cl", "Pure Water")'
        
        if 'price' in form.base_fields:
            form.base_fields['price'].label = 'Price (₦)'
            form.base_fields['price'].help_text = 'How much customers pay for this product in Naira'
        
        if 'category' in form.base_fields:
            form.base_fields['category'].label = 'Product Category'
            form.base_fields['category'].help_text = 'Which category this product belongs to (e.g., Bottled Water, Sachet Water)'
        
        if 'image' in form.base_fields:
            form.base_fields['image'].label = 'Product Image'
            form.base_fields['image'].help_text = 'Upload a photo of your product. Customers will see this image.'
        
        if 'sku' in form.base_fields:
            form.base_fields['sku'].label = 'Stock Quantity'
            form.base_fields['sku'].help_text = 'How many units of this product you currently have in stock'
        
        if 'is_available' in form.base_fields:
            form.base_fields['is_available'].label = 'Available for Order'
            form.base_fields['is_available'].help_text = 'Turn this off to temporarily hide the product from customers'
        
        return form
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            business_settings = self._get_business_settings()
            if business_settings:
                kwargs['queryset'] = Category.objects.filter(restaurant_settings=business_settings)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        """Show only products for this business."""
        qs = super().get_queryset(request).select_related('category', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()
    
    def _get_business_settings(self):
        """Get business settings from the current admin site."""
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    def price_display(self, obj):
        """Show price in Naira."""
        return f"₦{obj.price:,.2f}"
    price_display.short_description = 'Price'
    
    def stock_status(self, obj):
        """Show if product is in stock, low stock, or out of stock."""
        if obj.sku == 0:
            return format_html('<span style="color: #ef4444; font-weight: bold;">⚠️ Out of Stock</span>')
        elif obj.sku < 10:
            return format_html('<span style="color: #f59e0b; font-weight: bold;">⚠️ Low Stock - Only {} left!</span>', obj.sku)
        else:
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ In Stock ({} available)</span>', obj.sku)
    stock_status.short_description = 'Availability'
    
    def save_model(self, request, obj, form, change):
        """Automatically link product to this business."""
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        super().save_model(request, obj, form, change)


# ---- Inline for multiple product images ----
class MenuItemImageInline(admin.StackedInline):
    model = MenuItemImage
    extra = 3
    max_num = 20
    fields = ['image', 'sort_order']
    verbose_name = 'Additional image'
    verbose_name_plural = 'Additional images (upload multiple here)'
    ordering = ['sort_order', 'id']
    classes = []


# ---- ZMall forms and admin ----
import json
from .widgets import (
    ColorPickerWidget,
    CLOTHING_SIZE_CHOICES,
    SHOE_SIZE_CHOICES,
    ClothingSizeWidget,
    ShoeSizeWidget,
)


class ZmallMenuItemForm(forms.ModelForm):
    """Form for ZMall products: badges, sizes (by category), colors (picker), multiple images."""
    
    badge_choices = forms.MultipleChoiceField(
        label='Badges',
        choices=MenuItem.BADGE_CHOICES_ZMALL,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select badges shown on the product (ZMall only: Bestseller, Sale).',
    )
    size_clothing = forms.MultipleChoiceField(
        label='Sizes (clothing)',
        choices=CLOTHING_SIZE_CHOICES,
        required=False,
        widget=ClothingSizeWidget(),
        help_text='XS–XXL, ONE SIZE. Shown when category is not Shoes.',
    )
    size_shoes = forms.MultipleChoiceField(
        label='Sizes (shoes)',
        choices=SHOE_SIZE_CHOICES,
        required=False,
        widget=ShoeSizeWidget(),
        help_text='Shown only when category is Shoes.',
    )
    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'category', 'price', 'image', 'barcode',
            'gender', 'size_clothing', 'size_shoes', 'colors', 'sku', 'is_available', 'is_featured',
            'badge_choices',
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['badge_choices'].choices = MenuItem.BADGE_CHOICES_ZMALL
        self.fields['size_clothing'].choices = CLOTHING_SIZE_CHOICES
        self.fields['size_shoes'].choices = SHOE_SIZE_CHOICES
        self.fields['colors'].widget = ColorPickerWidget()
        self.fields['colors'].help_text = 'Add colours with optional names. Pick any shade; if name is empty, hex is shown on the store.'
        if self.instance and self.instance.pk:
            self.fields['image'].required = False
            if self.instance.badges:
                allowed = {c[0] for c in MenuItem.BADGE_CHOICES_ZMALL}
                self.fields['badge_choices'].initial = [b for b in self.instance.badges if b in allowed]
            if self.instance.sizes:
                shoe_vals = {c[0] for c in SHOE_SIZE_CHOICES}
                clothing_vals = {c[0] for c in CLOTHING_SIZE_CHOICES}
                self.fields['size_clothing'].initial = [s for s in self.instance.sizes if s in clothing_vals]
                self.fields['size_shoes'].initial = [s for s in self.instance.sizes if s in shoe_vals]
    
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.badges = self.cleaned_data.get('badge_choices', [])
        category = self.cleaned_data.get('category')
        is_shoes = category and getattr(category, 'slug', None) == 'shoes'
        obj.sizes = self.cleaned_data.get('size_shoes', []) if is_shoes else self.cleaned_data.get('size_clothing', [])
        if commit:
            obj.save()
        return obj


class ZmallCategoryAdmin(BusinessAdminMixin, ModelAdmin):
    """Categories for ZMall: keep slug safe for non-technical users."""
    
    list_display = ['name', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    ordering = ['name']
    list_editable = ['is_active']
    
    fieldsets = (
        (None, {'fields': ('name', 'description', 'image', 'is_active', 'sort_order')}),
        ('Advanced (do not change)', {
            'fields': ('slug',),
            'classes': ('collapse',),
            'description': 'This is used to build stable website URLs.',
        }),
    )
    readonly_fields = ('slug',)

    def save_model(self, request, obj, form, change):
        if not obj.restaurant_settings_id:
            obj.restaurant_settings = self._get_business_settings()
        if not obj.slug:
            base = slugify(obj.name)[:100] or f'category-{obj.pk or ""}'.strip('-')
            candidate = base
            n = 0
            rs = obj.restaurant_settings
            while Category.objects.filter(restaurant_settings=rs, slug=candidate).exclude(pk=obj.pk).exists():
                n += 1
                suffix = f'-{n}'
                candidate = f'{base[: (100 - len(suffix))]}{suffix}'
            obj.slug = candidate
        super().save_model(request, obj, form, change)
    
    def product_count(self, obj):
        business_settings = self._get_business_settings()
        if business_settings:
            return obj.menu_items.filter(restaurant_settings=business_settings).count()
        return 0
    product_count.short_description = 'Products'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        business_settings = self._get_business_settings()
        if not business_settings:
            return qs.none()
        return qs.filter(restaurant_settings=business_settings)
    
    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class ZmallMenuItemAdmin(BusinessAdminMixin, ModelAdmin):
    """Products for ZMall: apparel fields; colour picker; size checkboxes; multiple images."""
    
    form = ZmallMenuItemForm
    inlines = [MenuItemImageInline]
    change_form_template = 'admin/menu/menuitem/zmall_menuitem_change_form.html'

    class Media:
        js = ('menu/js/zmall_sizes.js',)
    list_display = ['name', 'category', 'gender', 'price_display', 'is_available', 'badges_display', 'sku', 'barcode']
    list_filter = [ZmallCategoryListFilter, 'gender', ZmallBadgeListFilter, 'is_available', 'is_featured']
    search_fields = ['name', 'description', 'category__name', 'barcode']
    ordering = ['category', '-created_at', 'name']
    list_editable = ['is_available', 'sku']
    
    fieldsets = (
        ('Product', {
            'fields': ('name', 'description', 'category', 'price', 'image', 'barcode'),
            'description': 'Product details.',
        }),
        ('Apparel', {
            'fields': ('gender', 'size_clothing', 'size_shoes', 'colors'),
            'description': 'Gender, sizes (checkboxes), and colours (picker; name optional, hex used when empty).',
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'sku'),
        }),
        ('Badges (ZMall only)', {
            'fields': ('badge_choices',),
            'description': 'Bestseller and Sale only.',
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('category', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            business_settings = self._get_business_settings()
            if business_settings:
                kwargs['queryset'] = Category.objects.filter(restaurant_settings=business_settings)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _zmall_extra_context(self, request):
        ctx = {}
        business_settings = self._get_business_settings()
        if business_settings:
            cat_qs = Category.objects.filter(restaurant_settings=business_settings)
            ctx['zmall_category_slugs_json'] = json.dumps({str(c.pk): (c.slug or '') for c in cat_qs})
        else:
            ctx['zmall_category_slugs_json'] = '{}'
        return ctx

    def add_view(self, request, form_url='', extra_context=None):
        extra = extra_context or {}
        extra.update(self._zmall_extra_context(request))
        return super().add_view(request, form_url, extra)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra = extra_context or {}
        extra.update(self._zmall_extra_context(request))
        return super().change_view(request, object_id, form_url, extra)

    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None
    
    def price_display(self, obj):
        return f"₦{obj.price:,.2f}"
    price_display.short_description = 'Price'
    
    def badges_display(self, obj):
        if not obj.badges:
            return ''
        allowed = {c[0] for c in MenuItem.BADGE_CHOICES_ZMALL}
        display = dict(MenuItem.BADGE_CHOICES_ZMALL)
        return ', '.join(display.get(b, b) for b in obj.badges if b in allowed)
    badges_display.short_description = 'Badges'
    
    def save_model(self, request, obj, form, change):
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        if not change and obj.category_id:
            agg = MenuItem.objects.filter(category_id=obj.category_id).aggregate(m=Max('sort_order'))
            obj.sort_order = (agg['m'] or 0) + 1
        super().save_model(request, obj, form, change)
        files = request.FILES.getlist('zmall_additional_images')
        if files and obj.pk:
            agg = obj.extra_images.aggregate(m=Max('sort_order'))
            next_order = (agg['m'] or 0) + 1
            for f in files:
                if f:
                    MenuItemImage.objects.create(menu_item=obj, image=f, sort_order=next_order)
                    next_order += 1


# Register with business admin sites
roschi_admin_site.register(Category, RoschiCategoryAdmin)
roschi_admin_site.register(MenuItem, RoschiMenuItemAdmin)
chopsticks_admin_site.register(Category, RoschiCategoryAdmin)
chopsticks_admin_site.register(MenuItem, RoschiMenuItemAdmin)
zmall_admin_site.register(Category, ZmallCategoryAdmin)
zmall_admin_site.register(MenuItem, ZmallMenuItemAdmin)
main_admin_site.register(Category, CategoryAdmin)
main_admin_site.register(MenuItem, MenuItemAdmin)
