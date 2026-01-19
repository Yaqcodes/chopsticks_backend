from django.test import TestCase

from core.models import RestaurantSettings
from .models import Order


class OrderModelFieldsTest(TestCase):
    def test_order_has_restaurant_settings_field(self):
        field = Order._meta.get_field('restaurant_settings')
        self.assertEqual(field.related_model, RestaurantSettings)
        self.assertFalse(field.null)
