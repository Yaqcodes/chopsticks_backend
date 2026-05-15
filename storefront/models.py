from django.core.exceptions import ValidationError
from django.db import models

from core.models import CatalogListingMode, RestaurantSettings


class SpotlightPlacement(models.TextChoices):
    """Known spotlight surfaces; extend as new homepage modules are added."""

    SHOP_THE_LOOK = 'shop_the_look', 'Shop the look (social carousel)'
    HOMEPAGE_CAROUSEL = 'homepage_carousel', 'Homepage carousel'


class SpotlightPost(models.Model):
    """Tenant-scoped visual spotlight tile (social, lookbook, featured set, etc.)."""

    restaurant_settings = models.ForeignKey(
        RestaurantSettings,
        on_delete=models.CASCADE,
        related_name='spotlight_posts',
    )
    image = models.ImageField(upload_to='storefront/')
    external_url = models.URLField(
        blank=True,
        help_text='Optional link (Instagram post, article, etc.).',
    )
    caption = models.CharField(max_length=255, blank=True)
    cta_label = models.CharField(
        max_length=64,
        blank=True,
        default='Shop the look',
        help_text='Short label shown on hover in the carousel.',
    )
    placement = models.SlugField(
        max_length=64,
        choices=SpotlightPlacement.choices,
        default=SpotlightPlacement.SHOP_THE_LOOK,
        db_index=True,
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at', 'id']
        verbose_name = 'Spotlight post'
        verbose_name_plural = 'Spotlight posts'
        indexes = [
            models.Index(fields=['restaurant_settings', 'placement', 'is_active', 'sort_order']),
        ]

    def __str__(self):
        return f'{self.get_placement_display()} #{self.pk}'


class SpotlightPostLink(models.Model):
    """Catalog row linked to a spotlight (whole look / featured set)."""

    spotlight = models.ForeignKey(
        SpotlightPost,
        on_delete=models.CASCADE,
        related_name='links',
    )
    product = models.ForeignKey(
        'menu.Product',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='spotlight_links',
    )
    menu_item = models.ForeignKey(
        'menu.MenuItem',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='spotlight_links',
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'Spotlight link'
        verbose_name_plural = 'Spotlight links'

    def __str__(self):
        if self.product_id:
            return f'Product {self.product_id}'
        if self.menu_item_id:
            return f'MenuItem {self.menu_item_id}'
        return 'Unlinked'

    def clean(self):
        super().clean()
        has_product = bool(self.product_id)
        has_menu_item = bool(self.menu_item_id)
        if has_product == has_menu_item:
            raise ValidationError('Link exactly one catalog row: Product or MenuItem.')

        spotlight = self.spotlight
        if not spotlight or not spotlight.restaurant_settings_id:
            return

        rs = spotlight.restaurant_settings
        mode = rs.catalog_listing_mode

        if mode == CatalogListingMode.PRODUCT:
            if not has_product:
                raise ValidationError('This business uses grouped Products; link a Product.')
            product_rs_id = (
                self.product.restaurant_settings_id
                if self.product_id and self.product is not None
                else None
            )
            if product_rs_id is None and self.product_id:
                from menu.models import Product
                product_rs_id = (
                    Product.objects.filter(pk=self.product_id)
                    .values_list('restaurant_settings_id', flat=True)
                    .first()
                )
            if product_rs_id != rs.id:
                raise ValidationError('Product must belong to this business.')
        else:
            if not has_menu_item:
                raise ValidationError('This business uses MenuItems; link a MenuItem.')
            menu_rs_id = (
                self.menu_item.restaurant_settings_id
                if self.menu_item_id and self.menu_item is not None
                else None
            )
            if menu_rs_id is None and self.menu_item_id:
                from menu.models import MenuItem
                menu_rs_id = (
                    MenuItem.objects.filter(pk=self.menu_item_id)
                    .values_list('restaurant_settings_id', flat=True)
                    .first()
                )
            if menu_rs_id != rs.id:
                raise ValidationError('MenuItem must belong to this business.')
