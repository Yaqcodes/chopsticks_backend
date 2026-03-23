from django.test import TestCase

from core.models import RestaurantSettings
from .models import MenuItem


class MenuItemModelFieldsTest(TestCase):
    def test_menu_item_has_size_field(self):
        field = MenuItem._meta.get_field('size')
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)

    def test_menu_item_has_sku_field(self):
        field = MenuItem._meta.get_field('sku')
        self.assertFalse(field.null)

    def test_menu_item_has_restaurant_settings_field(self):
        field = MenuItem._meta.get_field('restaurant_settings')
        self.assertEqual(field.related_model, RestaurantSettings)
        self.assertFalse(field.null)
