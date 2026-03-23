import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import RestaurantSettings


class RestaurantSettingsFieldsTest(TestCase):
    def test_restaurant_settings_has_domain_field(self):
        field = RestaurantSettings._meta.get_field('domain')
        self.assertTrue(field.unique)

    def test_restaurant_settings_has_paystack_fields(self):
        RestaurantSettings._meta.get_field('paystack_secret_key')
        RestaurantSettings._meta.get_field('paystack_public_key')
        RestaurantSettings._meta.get_field('paystack_webhook_secret')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SeedTenantsAndProductsCommandTest(TestCase):
    def test_seed_command_creates_tenants_and_products(self):
        call_command('seed_tenants_and_products')

        roschi = RestaurantSettings.objects.filter(domain='api.roschiwater.com').first()
        chopsticks = RestaurantSettings.objects.filter(domain='api.chopsticksandbowls.com').first()

        self.assertIsNotNone(roschi)
        self.assertIsNotNone(chopsticks)

        from menu.models import MenuItem

        roschi_items = MenuItem.objects.filter(restaurant_settings=roschi)
        self.assertEqual(roschi_items.count(), 4)
