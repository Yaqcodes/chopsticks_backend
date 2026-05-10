import re
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelect
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Count, Max
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import slugify
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.widgets import (
    UnfoldAdminDecimalFieldWidget,
    UnfoldAdminTextInputWidget,
    UnfoldBooleanWidget,
)
from .audit import log_product_variant_link
from .models import (
    Category,
    MenuItem,
    Product,
    ProductImage,
    ProductVariantLinkEvent,
)
from .product_link_service import link_menu_items_to_product
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
            ('preorder', 'Pre-Order'),
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

    class Media:
        js = ('menu/js/zmall_related_widget_fix.js',)


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
            'fields': ('name', 'description', 'size', 'sku', 'barcode', 'category', 'restaurant_settings', 'price', 'on_sale', 'sale_price', 'image')
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
            'fields': ('name', 'description', 'category', 'size', 'price', 'on_sale', 'sale_price', 'image'),
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


# ---- ZMall forms and admin ----
import json
from .widgets import ColorPickerWidget

ZMALL_BATCH_SALE_SESSION_KEY = 'menu_zmall_batch_sale_ids'
ZMALL_BATCH_LINK_SESSION_KEY = 'menu_zmall_batch_link_ids'


def _zmall_batch_sale_widget_classes():
    """Classes for standalone batch-sale template; inputs use Unfold, buttons use neutral zmall styles."""
    try:
        from unfold.widgets import INPUT_CLASSES

        return {
            'discount_input': ' '.join(INPUT_CLASSES),
            'submit': 'zmall-widget-btn zmall-widget-btn--primary',
            'cancel': 'zmall-widget-btn zmall-widget-btn--secondary',
        }
    except ImportError:
        return {
            'discount_input': 'zmall-admin-input',
            'submit': 'zmall-widget-btn zmall-widget-btn--primary',
            'cancel': 'zmall-widget-btn zmall-widget-btn--secondary',
        }


class ZmallMenuItemForm(forms.ModelForm):
    """Form for ZMall SKUs: one barcode per row; manual size on ``MenuItem.size``; colors picker."""
    
    badge_choices = forms.MultipleChoiceField(
        label='Badges',
        choices=MenuItem.BADGE_CHOICES_ZMALL,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select badges shown on the product (ZMall only: Bestseller, Sale).',
    )
    discount_percent_calculator = forms.DecimalField(
        label='Discount % (calculator)',
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=UnfoldAdminDecimalFieldWidget(),
        help_text='Optional. Enter 0–90 to set sale_price from list price (2 decimal places). Not stored; overwrites sale fields when saved.',
    )

    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'category', 'product', 'price', 'on_sale', 'sale_price', 'image', 'barcode',
            'gender', 'size', 'colors', 'sku', 'is_available', 'is_featured',
            'badge_choices', 'discount_percent_calculator',
        ]

    _size_max = MenuItem._meta.get_field('size').max_length

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['badge_choices'].choices = MenuItem.BADGE_CHOICES_ZMALL
        self.fields['size'].required = True
        self.fields['size'].widget = UnfoldAdminTextInputWidget()
        self.fields['size'].help_text = (
            'Required. One value per SKU row (e.g. 32, M, EU 42, One size). '
            'Same size with different colours should be separate products with different barcodes.'
        )
        self.fields['colors'].widget = ColorPickerWidget()
        self.fields['sale_price'].widget = UnfoldAdminDecimalFieldWidget()
        self.fields['on_sale'].widget = UnfoldBooleanWidget()
        self.fields['colors'].help_text = 'Add colours with optional names. Pick any shade; if name is empty, hex is shown on the store.'
        if self.instance and self.instance.pk:
            self.fields['image'].required = False
            if self.instance.badges:
                allowed = {c[0] for c in MenuItem.BADGE_CHOICES_ZMALL}
                self.fields['badge_choices'].initial = [b for b in self.instance.badges if b in allowed]
    
    def clean(self):
        cleaned = super().clean()
        pct = cleaned.get('discount_percent_calculator')
        if pct is not None and pct != '':
            try:
                p = Decimal(str(pct))
            except Exception:
                raise ValidationError({'discount_percent_calculator': 'Enter a valid percentage.'})
            if p <= 0 or p > 90:
                raise ValidationError(
                    {'discount_percent_calculator': 'Enter a percentage between 0.01 and 90, or leave blank.'}
                )
            price = cleaned.get('price')
            if price is None and self.instance and self.instance.pk:
                price = self.instance.price
            if price is None:
                raise ValidationError({'discount_percent_calculator': 'Set list price before using the calculator.'})
            factor = (Decimal('100') - p) / Decimal('100')
            sale = (price * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cleaned['sale_price'] = sale
            cleaned['on_sale'] = True

        return cleaned

    def clean_size(self):
        raw = self.cleaned_data.get('size', '')
        if raw is None:
            raw = ''
        s = str(raw).strip()
        if not s:
            raise ValidationError('Enter a size for this SKU (number or text, e.g. 32, M, EU 42).')
        if len(s) > self._size_max:
            raise ValidationError(f'Size must be at most {self._size_max} characters.')
        if re.search(r'[\r\n\t\x00]', s):
            raise ValidationError('Size cannot contain line breaks or other control characters.')
        return s

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.badges = self.cleaned_data.get('badge_choices', [])
        # Single-size SKU: ``size`` CharField is authoritative; clear JSON list to avoid
        # cartesian (sizes × colours) in variant_keys and legacy multi-size data.
        obj.sizes = []
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


class ZmallProductCategoryListFilter(admin.SimpleListFilter):
    """Category filter for grouped catalog Product model."""

    title = 'category'
    parameter_name = 'catalog_category'

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


class _ZmallInlinePermMixin:
    """
    Delegate inline view/change/delete/add permissions to the parent admin site
    instead of Django's model-level permission system.

    Without this, non-superuser ZMall staff users (who have business access via
    BusinessAdminSite.has_permission but no explicit menu.view_menuitem grants)
    would fail the default has_view_or_change_permission check and the inlines
    would be silently excluded from the change form.
    """

    def _site_has_permission(self, request):
        return self.admin_site.has_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._site_has_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._site_has_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self._site_has_permission(request)

    def has_add_permission(self, request, obj=None):
        return self._site_has_permission(request)


class ProductImageInline(_ZmallInlinePermMixin, StackedInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'sort_order']
    verbose_name = 'Gallery image'
    verbose_name_plural = 'Gallery images'


class LinkedVariantsInline(_ZmallInlinePermMixin, TabularInline):
    """Read-only view of MenuItem SKUs linked to this Product."""

    model = MenuItem
    fk_name = 'product'
    extra = 0
    can_delete = False
    verbose_name_plural = 'Linked variants'
    fields = (
        'variant_admin_link',
        'barcode',
        'sizes_preview',
        'colors_preview',
        'sku',
        'price',
        'is_available',
    )
    readonly_fields = (
        'variant_admin_link',
        'barcode',
        'sizes_preview',
        'colors_preview',
        'sku',
        'price',
        'is_available',
    )
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        # Variants are linked via the batch-link action, not added inline.
        return False

    def variant_admin_link(self, obj):
        if not obj.pk:
            return ''
        opts = MenuItem._meta
        name = self.admin_site.name
        url = reverse(f'{name}:{opts.app_label}_{opts.model_name}_change', args=[obj.pk])
        return format_html('<a href="{}">#{} — {}</a>', url, obj.pk, obj.name)

    variant_admin_link.short_description = 'SKU'

    def sizes_preview(self, obj):
        sizes = getattr(obj, 'sizes', None) or []
        out = [str(s).strip() for s in sizes if s and str(s).strip()]
        if not out and getattr(obj, 'size', ''):
            out = [obj.size]
        return ', '.join(out) if out else '—'

    sizes_preview.short_description = 'Sizes'

    def colors_preview(self, obj):
        colors = getattr(obj, 'colors', None) or []
        if isinstance(colors, list) and colors:
            parts = []
            for c in colors[:6]:
                if isinstance(c, dict) and c.get('name'):
                    parts.append(str(c['name']))
                elif c is not None and str(c).strip():
                    parts.append(str(c))
            if parts:
                return ', '.join(parts)
        return '—'

    colors_preview.short_description = 'Colours'


class ZmallProductForm(forms.ModelForm):
    """Grouped catalog Product: ZMall badges only."""

    badge_choices = forms.MultipleChoiceField(
        label='Badges',
        choices=Product.BADGE_CHOICES_ZMALL,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Shown on storefront for this grouped product.',
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'category',
            'gender',
            'base_price',
            'is_available',
            'is_featured',
            'sort_order',
            'meta_title',
            'meta_description',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['badge_choices'].choices = Product.BADGE_CHOICES_ZMALL
        if self.instance and self.instance.pk and self.instance.badges:
            allowed = {c[0] for c in Product.BADGE_CHOICES_ZMALL}
            self.fields['badge_choices'].initial = [b for b in self.instance.badges if b in allowed]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.badges = self.cleaned_data.get('badge_choices', [])
        if commit:
            obj.save()
        return obj


class ZmallProductAdmin(BusinessAdminMixin, ModelAdmin):
    """Grouped ZMall storefront product; variants are linked MenuItems."""

    form = ZmallProductForm
    change_form_template = 'admin/menu/product/zmall_product_change_form.html'
    inlines = [ProductImageInline, LinkedVariantsInline]
    list_display = [
        'name',
        'category',
        'gender',
        'price_display_base',
        'is_available',
        'is_featured',
        'variant_count',
        'slug',
    ]
    list_filter = [
        ZmallProductCategoryListFilter,
        'gender',
        ZmallBadgeListFilter,
        'is_available',
        'is_featured',
    ]
    search_fields = ['name', 'description', 'slug']
    ordering = ['sort_order', '-created_at', 'name']
    list_editable = ['is_available', 'is_featured']
    readonly_fields = ['slug']
    autocomplete_fields = ['category']
    actions = [
        'action_product_make_available',
        'action_product_make_unavailable',
    ]

    fieldsets = (
        ('Main info', {
            'fields': (
                'name',
                'description',
                'category',
                'gender',
                'base_price',
                'badge_choices',
            ),
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'sort_order'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'slug'),
            'classes': ('collapse',),
        }),
    )

    class Media:
        js = ('menu/js/zmall_related_widget_fix.js',)
        css = {'all': ('menu/css/zmall_admin_form.css',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('category', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings).annotate(
                _variant_num=Count('variants'),
            )
        return qs.none()

    def variant_count(self, obj):
        c = getattr(obj, '_variant_num', None)
        if c is not None:
            return c
        return obj.variants.count()

    variant_count.short_description = 'Variants'

    def price_display_base(self, obj):
        return f"₦{obj.base_price:,.2f}"

    price_display_base.short_description = 'Base price'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            business_settings = self._get_business_settings()
            if business_settings:
                kwargs['queryset'] = Category.objects.filter(restaurant_settings=business_settings)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        if not obj.slug:
            rs = obj.restaurant_settings
            base = slugify(obj.name)[:100] or 'product'
            candidate = base
            n = 0
            while Product.objects.filter(restaurant_settings=rs, slug=candidate).exclude(pk=obj.pk).exists():
                n += 1
                suffix = f'-{n}'
                candidate = f'{base[: (100 - len(suffix))]}{suffix}'
            obj.slug = candidate
        super().save_model(request, obj, form, change)

    def action_product_make_available(self, request, queryset):
        n = queryset.update(is_available=True)
        self.message_user(request, f'Marked {n} catalog product(s) as available.', level=messages.SUCCESS)

    action_product_make_available.short_description = 'Make available'

    def action_product_make_unavailable(self, request, queryset):
        n = queryset.update(is_available=False)
        self.message_user(request, f'Marked {n} catalog product(s) as unavailable.', level=messages.SUCCESS)

    action_product_make_unavailable.short_description = 'Make unavailable'

    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None


class ZmallMenuItemAdmin(BusinessAdminMixin, ModelAdmin):
    """ZMall SKUs: manual size per row, colour picker; one barcode per MenuItem."""

    form = ZmallMenuItemForm
    change_form_template = 'admin/menu/menuitem/zmall_menuitem_change_form.html'
    actions = [
        'action_link_to_catalog_product',
        'action_apply_sale_discount',
        'action_batch_remove_sale',
        'action_clear_sale',
        'action_variant_make_available',
        'action_variant_make_unavailable',
    ]

    class Media:
        js = ('menu/js/zmall_related_widget_fix.js',)
        css = {'all': ('menu/css/zmall_admin_form.css',)}
    list_display = [
        'name', 'category', 'catalog_product_link', 'gender', 'price_display',
        'is_available', 'badges_display', 'sku', 'barcode',
    ]
    list_filter = [ZmallCategoryListFilter, 'gender', ZmallBadgeListFilter, 'is_available', 'is_featured', 'on_sale']
    search_fields = ['name', 'description', 'category__name', 'barcode']
    ordering = ['category', '-created_at', 'name']
    list_editable = ['is_available', 'sku']
    autocomplete_fields = ['category', 'product']
    
    fieldsets = (
        ('Product', {
            'fields': ('name', 'description', 'category', 'product', 'price', 'image', 'barcode'),
            'description': 'SKU / variant row. Optionally link to a grouped catalog Product (ZMall storefront).',
        }),
        ('Apparel', {
            'fields': ('gender', 'size', 'colors'),
            'description': 'Each row is one SKU (one barcode). Enter the size for this row only; use another row for the same size in a different colour.',
        }),
        ('Sale', {
            'fields': ('on_sale', 'sale_price', 'discount_percent_calculator'),
            'description': 'List price is in Product. Optional calculator sets sale from % (max 90); not stored.',
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'sku'),
        }),
        ('Badges (ZMall only)', {
            'fields': ('badge_choices',),
            'description': 'Bestseller and Sale only.',
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path(
                'batch-apply-sale/',
                self.admin_site.admin_view(self.batch_apply_sale_view),
                name='%s_%s_batch_apply_sale' % info,
            ),
            path(
                'unlinked-skus-report/',
                self.admin_site.admin_view(self.unlinked_skus_report_view),
                name='%s_%s_unlinked_skus' % info,
            ),
            path(
                'batch-link-product/',
                self.admin_site.admin_view(self.batch_link_product_view),
                name='%s_%s_batch_link_product' % info,
            ),
        ]
        return custom + urls

    def action_link_to_catalog_product(self, request, queryset):
        ids = list(queryset.values_list('pk', flat=True))
        if not ids:
            self.message_user(request, 'No SKUs selected.', level=messages.WARNING)
            return
        request.session[ZMALL_BATCH_LINK_SESSION_KEY] = ids
        opts = self.model._meta
        url = reverse(
            '%s:%s_%s_batch_link_product'
            % (self.admin_site.name, opts.app_label, opts.model_name),
        )
        return HttpResponseRedirect(url)

    action_link_to_catalog_product.short_description = 'Link to catalog Product (existing or new)…'

    def _build_batch_link_form(self, request, business_settings, data=None):
        site = self.admin_site
        product_field = MenuItem._meta.get_field('product')
        category_field = MenuItem._meta.get_field('category')

        product_qs = Product.objects.filter(restaurant_settings=business_settings).order_by('name')
        category_qs = Category.objects.filter(restaurant_settings=business_settings).order_by('name')

        class BatchLinkForm(forms.Form):
            mode = forms.ChoiceField(
                choices=(('existing', 'Link to existing product'), ('new', 'Create new product')),
                widget=forms.RadioSelect,
                initial='existing',
            )
            product = forms.ModelChoiceField(
                label='Catalog product',
                queryset=product_qs,
                required=False,
                widget=AutocompleteSelect(product_field, site),
                help_text='Search by product name.',
            )
            name = forms.CharField(label='New product name', max_length=200, required=False)
            category = forms.ModelChoiceField(
                label='Category',
                queryset=category_qs,
                required=False,
                widget=AutocompleteSelect(category_field, site),
            )
            gender = forms.ChoiceField(
                label='Gender',
                choices=[('', '—')] + list(MenuItem.GENDER_CHOICES),
                required=False,
            )
            base_price = forms.DecimalField(
                label='Base price (informational)',
                required=False,
                min_value=Decimal('0'),
                decimal_places=2,
                max_digits=10,
                initial=Decimal('0.00'),
            )

            def clean(self):
                cleaned = super().clean()
                if cleaned.get('mode') == 'existing':
                    if not cleaned.get('product'):
                        raise forms.ValidationError(
                            {'product': 'Pick an existing product or switch to “Create new”.'},
                        )
                else:
                    if not (cleaned.get('name') or '').strip():
                        raise forms.ValidationError({'name': 'Product name is required when creating a new product.'})
                    if not cleaned.get('category'):
                        raise forms.ValidationError({'category': 'Category is required when creating a new product.'})
                return cleaned

        return BatchLinkForm(data) if data is not None else BatchLinkForm()

    def batch_link_product_view(self, request):
        opts = self.model._meta
        site = self.admin_site.name
        session_key = ZMALL_BATCH_LINK_SESSION_KEY
        raw_ids = request.session.get(session_key) or []
        business_settings = self._get_business_settings()
        changelist_url = reverse('%s:%s_%s_changelist' % (site, opts.app_label, opts.model_name))
        admin_index_url = reverse('%s:index' % site)

        if not raw_ids:
            messages.warning(request, 'No SKUs in batch. Select rows and choose “Link to catalog Product” again.')
            return HttpResponseRedirect(changelist_url)
        if not business_settings:
            messages.error(request, 'Could not resolve business for this admin site.')
            return HttpResponseRedirect(changelist_url)

        skus_qs = (
            self.model.objects.filter(pk__in=raw_ids, restaurant_settings=business_settings)
            .select_related('category', 'product')
            .order_by('name')
        )
        valid_ids = set(skus_qs.values_list('pk', flat=True))
        if valid_ids != set(raw_ids):
            del request.session[session_key]
            messages.error(request, 'Invalid or expired selection.')
            return HttpResponseRedirect(changelist_url)

        if request.method == 'POST':
            form = self._build_batch_link_form(request, business_settings, data=request.POST)
            if not form.is_valid():
                return self._render_batch_link(
                    request, skus_qs, form, changelist_url, admin_index_url, opts,
                )
            cleaned = form.cleaned_data
            mode = cleaned['mode']
            if mode == 'existing':
                product = cleaned['product']
            else:
                name = cleaned['name'].strip()
                base_slug = slugify(name)[:100] or 'product'
                candidate = base_slug
                n = 0
                while Product.objects.filter(
                    restaurant_settings=business_settings, slug=candidate,
                ).exists():
                    n += 1
                    suffix = f'-{n}'
                    candidate = f'{base_slug[: (100 - len(suffix))]}{suffix}'
                product = Product.objects.create(
                    restaurant_settings=business_settings,
                    name=name,
                    description='',
                    category=cleaned['category'],
                    gender=cleaned.get('gender') or None,
                    base_price=cleaned.get('base_price') or Decimal('0.00'),
                    slug=candidate,
                )
                messages.success(request, f'Created new catalog product “{product.name}”.')

            skus = list(skus_qs)
            result = link_menu_items_to_product(product, skus, dry_run=False)
            errs = result.get('errors') or []
            if errs:
                first = errs[0].get('message', errs[0])
                messages.error(request, f'Could not link some SKUs. First error: {first}')
                return self._render_batch_link(
                    request, skus_qs, form, changelist_url, admin_index_url, opts,
                )

            linked = result.get('linked_ids') or []
            for mid, prev in result.get('linked_events', []):
                log_product_variant_link(
                    request,
                    action='link',
                    product_id=product.pk,
                    menu_item_id=mid,
                    previous_product_id=prev,
                    restaurant_settings=business_settings,
                )
            del request.session[session_key]
            if not linked:
                messages.info(request, 'No SKUs linked (already linked to this product).')
            else:
                messages.success(
                    request,
                    f'Linked {len(linked)} SKU(s) to “{product.name}”.',
                )
            product_change_url = reverse(
                '%s:%s_%s_change' % (site, Product._meta.app_label, Product._meta.model_name),
                args=[product.pk],
            )
            return HttpResponseRedirect(product_change_url)

        form = self._build_batch_link_form(request, business_settings)
        return self._render_batch_link(request, skus_qs, form, changelist_url, admin_index_url, opts)

    def _render_batch_link(self, request, skus_qs, form, changelist_url, admin_index_url, opts):
        site = self.admin_site.name
        product_change_url_name = '%s:%s_%s_change' % (
            site, Product._meta.app_label, Product._meta.model_name,
        )
        sku_change_url_name = '%s:%s_%s_change' % (site, opts.app_label, opts.model_name)
        context = {
            **self.admin_site.each_context(request),
            'title': 'Link SKUs to catalog Product',
            'opts': opts,
            'queryset': skus_qs,
            'form': form,
            'product_change_url_name': product_change_url_name,
            'sku_change_url_name': sku_change_url_name,
            'changelist_url': changelist_url,
            'admin_index_url': admin_index_url,
            'has_permission': True,
        }
        return TemplateResponse(request, 'admin/menu/batch_link_product.html', context)

    def unlinked_skus_report_view(self, request):
        business_settings = self._get_business_settings()
        opts = self.model._meta
        site = self.admin_site.name
        changelist_url = reverse('%s:%s_%s_changelist' % (site, opts.app_label, opts.model_name))
        admin_index_url = reverse('%s:index' % site)

        if request.method == 'POST' and business_settings:
            product_id = request.POST.get('product_id')
            raw_ids = request.POST.getlist('menuitem_id')
            if not product_id or not raw_ids:
                self.message_user(request, 'Select a catalog product and at least one SKU.', level=messages.WARNING)
            else:
                product = get_object_or_404(
                    Product.objects.filter(restaurant_settings=business_settings),
                    pk=product_id,
                )
                skus = list(
                    self.model.objects.filter(
                        pk__in=raw_ids,
                        restaurant_settings=business_settings,
                        product__isnull=True,
                    ),
                )
                result = link_menu_items_to_product(product, skus, dry_run=False)
                errs = result.get('errors') or []
                if errs:
                    self.message_user(
                        request,
                        'Could not link some SKUs. First error: %s' % (errs[0].get('message', errs[0])),
                        level=messages.ERROR,
                    )
                else:
                    linked = result.get('linked_ids') or []
                    if not linked:
                        self.message_user(request, 'No SKUs linked (nothing selected or already linked).', level=messages.INFO)
                    else:
                        for mid, prev in result.get('linked_events', []):
                            log_product_variant_link(
                                request,
                                action='link',
                                product_id=product.pk,
                                menu_item_id=mid,
                                previous_product_id=prev,
                                restaurant_settings=business_settings,
                            )
                        self.message_user(
                            request,
                            f'Linked {len(linked)} SKU(s) to “{product.name}”.',
                            level=messages.SUCCESS,
                        )
            return HttpResponseRedirect(request.path)

        tenant_resolved = business_settings is not None
        items = self.model.objects.none()
        products_qs = Product.objects.none()
        if business_settings:
            items = (
                self.model.objects.filter(
                    restaurant_settings=business_settings,
                    product__isnull=True,
                )
                .select_related('category')
                .order_by('name')
            )
            products_qs = Product.objects.filter(restaurant_settings=business_settings).order_by('name')

        item_change_url_name = '%s:%s_%s_change' % (site, opts.app_label, opts.model_name)
        has_catalog_products = tenant_resolved and products_qs.exists()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Unlinked SKUs (no catalog Product)',
            'items': items,
            'catalog_products': products_qs,
            'tenant_resolved': tenant_resolved,
            'has_catalog_products': has_catalog_products,
            'opts': opts,
            'changelist_url': changelist_url,
            'admin_index_url': admin_index_url,
            'item_change_url_name': item_change_url_name,
            'has_permission': True,
        }
        return TemplateResponse(request, 'admin/menu/unlinked_skus_report.html', context)

    def action_apply_sale_discount(self, request, queryset):
        ids = list(queryset.values_list('pk', flat=True))
        if not ids:
            self.message_user(request, 'No products selected.', level=messages.WARNING)
            return
        request.session[ZMALL_BATCH_SALE_SESSION_KEY] = ids
        opts = self.model._meta
        url = reverse(
            '%s:%s_%s_batch_apply_sale'
            % (self.admin_site.name, opts.app_label, opts.model_name),
        )
        return HttpResponseRedirect(url)

    action_apply_sale_discount.short_description = 'Apply sale discount %%…'

    def action_batch_remove_sale(self, request, queryset):
        n = queryset.update(on_sale=False)
        self.message_user(request, f'Set on_sale=false for {n} product(s).', level=messages.SUCCESS)

    action_batch_remove_sale.short_description = 'Take off sale (on_sale only)'

    def action_clear_sale(self, request, queryset):
        n = queryset.update(on_sale=False, sale_price=None)
        self.message_user(request, f'Cleared sale on {n} product(s).', level=messages.SUCCESS)

    action_clear_sale.short_description = 'Clear sale (off + wipe sale price)'

    def batch_apply_sale_view(self, request):
        session_key = ZMALL_BATCH_SALE_SESSION_KEY
        raw_ids = request.session.get(session_key)
        if not raw_ids:
            messages.warning(request, 'No products in batch. Select items and choose “Apply sale discount %” again.')
            return HttpResponseRedirect(self._changelist_url())

        qs = self.model.objects.filter(pk__in=raw_ids)
        business_settings = self._get_business_settings()
        if business_settings:
            qs = qs.filter(restaurant_settings=business_settings)
        valid_ids = set(qs.values_list('pk', flat=True))
        if valid_ids != set(raw_ids):
            del request.session[session_key]
            messages.error(request, 'Invalid or expired selection.')
            return HttpResponseRedirect(self._changelist_url())

        if request.method == 'POST':
            pct_raw = (request.POST.get('discount_percent') or '').strip()
            try:
                pct = Decimal(pct_raw)
            except Exception:
                messages.error(request, 'Enter a valid percentage.')
                context = self._batch_sale_context(request, qs)
                return TemplateResponse(request, 'admin/menu/menuitem/batch_apply_sale.html', context)
            if pct <= 0 or pct > 90:
                messages.error(request, 'Discount must be between 0.01 and 90%.')
                context = self._batch_sale_context(request, qs)
                return TemplateResponse(request, 'admin/menu/menuitem/batch_apply_sale.html', context)
            factor = (Decimal('100') - pct) / Decimal('100')
            for obj in qs:
                obj.sale_price = (obj.price * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                obj.on_sale = True
                obj.save(update_fields=['sale_price', 'on_sale'])
            del request.session[session_key]
            messages.success(request, f'Applied {pct}% sale to {qs.count()} product(s).')
            return HttpResponseRedirect(self._changelist_url())

        context = self._batch_sale_context(request, qs)
        return TemplateResponse(request, 'admin/menu/menuitem/batch_apply_sale.html', context)

    def _changelist_url(self):
        opts = self.model._meta
        return reverse(
            '%s:%s_%s_changelist'
            % (self.admin_site.name, opts.app_label, opts.model_name),
        )

    def _batch_sale_context(self, request, queryset):
        opts = self.model._meta
        site = self.admin_site.name
        wc = _zmall_batch_sale_widget_classes()
        return {
            **self.admin_site.each_context(request),
            'title': 'Apply sale discount',
            'opts': opts,
            'queryset': queryset,
            'changelist_url': self._changelist_url(),
            'admin_index_url': reverse('%s:index' % site),
            'has_permission': True,
            'zmall_batch_discount_input_class': wc['discount_input'],
            'zmall_batch_submit_class': wc['submit'],
            'zmall_batch_cancel_class': wc['cancel'],
        }
    
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
        if db_field.name == 'product':
            kwargs['required'] = False
            business_settings = self._get_business_settings()
            if business_settings:
                kwargs['queryset'] = Product.objects.filter(restaurant_settings=business_settings).order_by(
                    'name',
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def catalog_product_link(self, obj):
        if not getattr(obj, 'product_id', None):
            return '—'
        p = getattr(obj, 'product', None)
        if not p:
            return '—'
        try:
            url = reverse(f'{self.admin_site.name}:{Product._meta.app_label}_{Product._meta.model_name}_change', args=[p.pk])
            return format_html('<a href="{}">{}</a>', url, p.name)
        except Exception:
            return p.name

    catalog_product_link.short_description = 'Catalog Product'

    def action_variant_make_available(self, request, queryset):
        n = queryset.update(is_available=True)
        self.message_user(request, f'Marked {n} SKU(s) as available.', level=messages.SUCCESS)

    action_variant_make_available.short_description = 'Make available'

    def action_variant_make_unavailable(self, request, queryset):
        n = queryset.update(is_available=False)
        self.message_user(request, f'Marked {n} SKU(s) as unavailable.', level=messages.SUCCESS)

    action_variant_make_unavailable.short_description = 'Make unavailable'

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
        if getattr(obj, 'on_sale', False) and obj.sale_price is not None:
            list_fmt = '{:,.2f}'.format(obj.price)
            sale_fmt = '{:,.2f}'.format(obj.sale_price)
            return format_html(
                '<span style="text-decoration:line-through">₦{}</span> '
                '<strong>₦{}</strong>',
                list_fmt,
                sale_fmt,
            )
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
        old_product_id = None
        if change and obj.pk:
            old_product_id = (
                MenuItem.objects.filter(pk=obj.pk).values_list('product_id', flat=True).first()
            )
        if not obj.restaurant_settings_id:
            business_settings = self._get_business_settings()
            if business_settings:
                obj.restaurant_settings = business_settings
        if not change and obj.category_id:
            agg = MenuItem.objects.filter(category_id=obj.category_id).aggregate(m=Max('sort_order'))
            obj.sort_order = (agg['m'] or 0) + 1
        super().save_model(request, obj, form, change)

        rs_audit = obj.restaurant_settings if obj.restaurant_settings_id else None
        if rs_audit is None:
            rs_audit = self._get_business_settings()
        new_pid = obj.product_id
        if rs_audit:
            if not change and new_pid:
                log_product_variant_link(
                    request,
                    action='link',
                    product_id=new_pid,
                    menu_item_id=obj.pk,
                    previous_product_id=None,
                    restaurant_settings=rs_audit,
                )
            elif change and old_product_id != new_pid:
                if new_pid is None and old_product_id:
                    log_product_variant_link(
                        request,
                        action='unlink',
                        product_id=old_product_id,
                        menu_item_id=obj.pk,
                        previous_product_id=old_product_id,
                        restaurant_settings=rs_audit,
                    )
                elif new_pid:
                    log_product_variant_link(
                        request,
                        action='link',
                        product_id=new_pid,
                        menu_item_id=obj.pk,
                        previous_product_id=old_product_id,
                        restaurant_settings=rs_audit,
                    )


class ProductVariantLinkEventAdmin(BusinessAdminMixin, ModelAdmin):
    """Read-only audit list for variant link/unlink (ZMall storefront admin)."""

    list_display = (
        'created_at',
        'action',
        'product_id',
        'menu_item_id',
        'previous_product_id',
        'acting_user',
    )
    list_filter = ('action', 'created_at')
    search_fields = ('menu_item_id', 'product_id', 'previous_product_id')
    readonly_fields = (
        'created_at',
        'acting_user',
        'restaurant_settings',
        'action',
        'product_id',
        'menu_item_id',
        'previous_product_id',
    )
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('acting_user', 'restaurant_settings')
        business_settings = self._get_business_settings()
        if business_settings:
            return qs.filter(restaurant_settings=business_settings)
        return qs.none()

    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Register with business admin sites
roschi_admin_site.register(Category, RoschiCategoryAdmin)
roschi_admin_site.register(MenuItem, RoschiMenuItemAdmin)
chopsticks_admin_site.register(Category, RoschiCategoryAdmin)
chopsticks_admin_site.register(MenuItem, RoschiMenuItemAdmin)
zmall_admin_site.register(Category, ZmallCategoryAdmin)
zmall_admin_site.register(Product, ZmallProductAdmin)
zmall_admin_site.register(ProductVariantLinkEvent, ProductVariantLinkEventAdmin)
zmall_admin_site.register(MenuItem, ZmallMenuItemAdmin)
main_admin_site.register(Category, CategoryAdmin)
main_admin_site.register(MenuItem, MenuItemAdmin)
