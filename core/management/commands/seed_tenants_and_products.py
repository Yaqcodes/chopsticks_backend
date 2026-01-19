from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from core.models import RestaurantSettings
from menu.models import Category, MenuItem


class Command(BaseCommand):
    help = "Seed tenants and Roschi water products with images."

    def handle(self, *args, **options):
        project_root = Path(settings.BASE_DIR).parent
        assets_dir = project_root / 'public' / 'assets'

        if not assets_dir.exists():
            self.stderr.write(self.style.ERROR(f"Assets directory not found: {assets_dir}"))
            return

        roschi, _ = RestaurantSettings.objects.update_or_create(
            domain='api.roschiwater.com',
            defaults={
                'name': 'Roschi Water',
                'description': 'Premium table water and sachet water',
                'tagline': 'Refreshing, clean, and hygienic',
                'address': 'Abuja, Nigeria',
                'phone': '+234',
                'email': 'info@roschiwater.com',
                'website': 'https://roschiwater.com',
                'vat_rate': 0.075,
                'accepts_cash': True,
                'accepts_card': True,
                'accepts_mobile_money': True,
            },
        )

        RestaurantSettings.objects.update_or_create(
            domain='api.chopsticksandbowls.com',
            defaults={
                'name': 'Chopsticks and Bowls',
                'description': 'Authentic Korean Cuisine in Abuja',
                'tagline': 'Authentic Korean Cuisine in Abuja',
                'address': 'Abuja, Nigeria',
                'phone': '+234',
                'email': 'info@chopsticksandbowls.com',
                'website': 'https://chopsticksandbowls.com',
                'vat_rate': 0.075,
                'accepts_cash': True,
                'accepts_card': True,
                'accepts_mobile_money': True,
            },
        )

        bottled_category, _ = Category.objects.get_or_create(
            name='Bottled Water',
            defaults={'description': 'Bottled water products', 'is_active': True, 'sort_order': 1},
        )
        sachet_category, _ = Category.objects.get_or_create(
            name='Sachet Water',
            defaults={'description': 'Sachet water products', 'is_active': True, 'sort_order': 2},
        )

        products = [
            {
                'name': 'ROSCHI Bottled Water',
                'size': '24-pack 35cl',
                'price': 2500,
                'sku': 100,
                'category': bottled_category,
                'description': 'Pure, refreshing bottled water',
                'image_filename': 'bottle_gen3_35.png',
            },
            {
                'name': 'ROSCHI Bottled Water',
                'size': '20-pack 50cl',
                'price': 2700,
                'sku': 50,
                'category': bottled_category,
                'description': 'Convenient 20-pack bundle',
                'image_filename': 'bottle_gen3_50.jpg',
            },
            {
                'name': 'ROSCHI Bottled Water',
                'size': '12-pack 75cl',
                'price': 1800,
                'sku': 75,
                'category': bottled_category,
                'description': 'Larger size for your convenience',
                'image_filename': 'bottle_gen3_75.png',
            },
            {
                'name': 'ROSCHI Sachet Water',
                'size': 'Pure Water',
                'price': 300,
                'sku': 200,
                'category': sachet_category,
                'description': 'Affordable sachet water (20pcs)',
                'image_filename': 'purewater.png',
            },
        ]

        for product in products:
            menu_item, _ = MenuItem.objects.update_or_create(
                name=product['name'],
                size=product['size'],
                restaurant_settings=roschi,
                defaults={
                    'description': product['description'],
                    'price': product['price'],
                    'category': product['category'],
                    'sku': product['sku'],
                    'is_available': True,
                    'is_featured': False,
                },
            )

            image_path = assets_dir / product['image_filename']
            if image_path.exists():
                with image_path.open('rb') as image_file:
                    menu_item.image.save(product['image_filename'], File(image_file), save=True)
            else:
                self.stderr.write(self.style.WARNING(f"Image not found: {image_path}"))

        self.stdout.write(self.style.SUCCESS("Tenants and Roschi products seeded successfully."))
