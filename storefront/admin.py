from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from unfold.admin import ModelAdmin, TabularInline

from core.admin_sites import chopsticks_admin_site, roschi_admin_site, zmall_admin_site
from core.main_admin_site import main_admin_site
from core.models import CatalogListingMode
from menu.admin import BusinessAdminMixin
from menu.models import MenuItem, Product

from .models import SpotlightPost, SpotlightPostLink


MAX_LINKS_PER_SPOTLIGHT = 12


class SpotlightPostLinkFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        count = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            count += 1
        if count > MAX_LINKS_PER_SPOTLIGHT:
            raise ValidationError(
                f'At most {MAX_LINKS_PER_SPOTLIGHT} catalog links per spotlight.'
            )


class SpotlightPostLinkInline(TabularInline):
    model = SpotlightPostLink
    formset = SpotlightPostLinkFormSet
    extra = 1
    min_num = 0
    ordering = ['sort_order']
    fields = ['product', 'menu_item', 'sort_order']
    # Declared empty: Product is only registered on zmall_admin_site (E039 otherwise).
    autocomplete_fields = ()

    class Media:
        js = ('menu/js/zmall_related_widget_fix.js',)

    def _model_on_site(self, model):
        return model in self.admin_site._registry

    def _catalog_mode(self, request):
        attr = '_spotlight_catalog_mode'
        if hasattr(request, attr):
            return getattr(request, attr)
        business = None
        if hasattr(self.admin_site, 'get_business_settings'):
            business = self.admin_site.get_business_settings()
        mode = business.catalog_listing_mode if business else CatalogListingMode.MENU_ITEM
        setattr(request, attr, mode)
        return mode

    def get_fields(self, request, obj=None):
        if self._catalog_mode(request) == CatalogListingMode.PRODUCT:
            return ['product', 'sort_order']
        return ['menu_item', 'sort_order']

    def get_autocomplete_fields(self, request):
        mode = self._catalog_mode(request)
        if mode == CatalogListingMode.PRODUCT and self._model_on_site(Product):
            return ['product']
        if mode == CatalogListingMode.MENU_ITEM and self._model_on_site(MenuItem):
            return ['menu_item']
        return []

    def get_raw_id_fields(self, request, obj=None):
        """Fallback when the linked model is not registered on this admin site."""
        mode = self._catalog_mode(request)
        if mode == CatalogListingMode.PRODUCT and not self._model_on_site(Product):
            return ['product']
        if mode == CatalogListingMode.MENU_ITEM and not self._model_on_site(MenuItem):
            return ['menu_item']
        return []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        business = None
        if hasattr(self.admin_site, 'get_business_settings'):
            business = self.admin_site.get_business_settings()
        if business:
            if db_field.name == 'product':
                kwargs['queryset'] = Product.objects.filter(restaurant_settings=business)
            elif db_field.name == 'menu_item':
                kwargs['queryset'] = MenuItem.objects.filter(restaurant_settings=business)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SpotlightPostAdmin(BusinessAdminMixin, ModelAdmin):
    list_display = [
        'placement',
        'sort_order',
        'is_active',
        'cta_label',
        'link_count',
        'updated_at',
    ]
    list_filter = ['placement', 'is_active']
    search_fields = ['caption', 'cta_label', 'external_url']
    list_editable = ['sort_order', 'is_active']
    ordering = ['placement', 'sort_order', '-created_at']
    inlines = [SpotlightPostLinkInline]

    fieldsets = (
        (None, {
            'fields': (
                'image',
                'external_url',
                'caption',
                'cta_label',
                'placement',
                'sort_order',
                'is_active',
            ),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('restaurant_settings')
        business = self._get_business_settings()
        if business:
            return qs.filter(restaurant_settings=business)
        return qs

    def save_model(self, request, obj, form, change):
        if not obj.restaurant_settings_id:
            business = self._get_business_settings()
            if business:
                obj.restaurant_settings = business
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.full_clean()
            instance.save()
        for instance in formset.deleted_objects:
            instance.delete()
        formset.save_m2m()

    def link_count(self, obj):
        return obj.links.count()

    link_count.short_description = 'Links'

    def _get_business_settings(self):
        if hasattr(self.admin_site, 'get_business_settings'):
            return self.admin_site.get_business_settings()
        return None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'restaurant_settings':
            kwargs['queryset'] = kwargs.get('queryset', db_field.remote_field.model.objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class MainSpotlightPostAdmin(SpotlightPostAdmin):
    """Main admin: show tenant field for superusers."""

    fieldsets = (
        ('Business', {'fields': ('restaurant_settings',)}),
        (None, {
            'fields': (
                'image',
                'external_url',
                'caption',
                'cta_label',
                'placement',
                'sort_order',
                'is_active',
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        return self.fieldsets


zmall_admin_site.register(SpotlightPost, SpotlightPostAdmin)
roschi_admin_site.register(SpotlightPost, SpotlightPostAdmin)
chopsticks_admin_site.register(SpotlightPost, SpotlightPostAdmin)
main_admin_site.register(SpotlightPost, MainSpotlightPostAdmin)
