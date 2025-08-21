from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from menu.models import Category, MenuItem
from loyalty.models import UserPoints, Reward, LoyaltyCard
from promotions.models import PromoCode
# from core.models import SystemSetting  # Not available
from addresses.models import Address
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Create dummy data using Django ORM'

    def handle(self, *args, **options):
        self.stdout.write('Creating dummy data...')
        
        with transaction.atomic():
            self.create_menu_data()
            self.create_loyalty_data()
            self.create_promotions_data()
            # self.create_system_settings()  # Not available
            self.create_addresses()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Dummy data created successfully!')
        )

    def create_menu_data(self):
        """Create menu categories and items"""
        self.stdout.write('Creating menu data...')
        
        # Categories
        categories = [
            {'name': 'Appetizers', 'description': 'Start your meal right', 'sort_order': 1},
            {'name': 'Soups', 'description': 'Warm and comforting soups', 'sort_order': 2},
            {'name': 'Main Dishes', 'description': 'Our signature main courses', 'sort_order': 3},
            {'name': 'Rice & Noodles', 'description': 'Traditional rice and noodle dishes', 'sort_order': 4},
            {'name': 'Desserts', 'description': 'Sweet endings to your meal', 'sort_order': 5},
            {'name': 'Beverages', 'description': 'Refreshing drinks and teas', 'sort_order': 6},
        ]
        
        created_categories = {}
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'is_active': True,
                    'sort_order': cat_data['sort_order']
                }
            )
            created_categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Menu Items
        menu_items = [
            {
                'name': 'Spring Rolls',
                'description': 'Fresh vegetables wrapped in rice paper with sweet chili sauce',
                'price': 8.99,
                'category': 'Appetizers',
                'is_featured': True,
                'badges': ['vegetarian', 'popular'],
                'allergens': ['nuts'],
                'nutritional_info': {'calories': 120, 'protein': 3, 'carbs': 15}
            },
            {
                'name': 'Dumplings',
                'description': 'Steamed pork and vegetable dumplings',
                'price': 10.99,
                'category': 'Appetizers',
                'is_featured': True,
                'badges': ['popular'],
                'allergens': ['gluten', 'pork'],
                'nutritional_info': {'calories': 180, 'protein': 8, 'carbs': 20}
            },
            {
                'name': 'Kung Pao Chicken',
                'description': 'Spicy diced chicken with peanuts and vegetables',
                'price': 16.99,
                'category': 'Main Dishes',
                'is_featured': True,
                'badges': ['spicy', 'popular'],
                'allergens': ['nuts', 'chicken'],
                'nutritional_info': {'calories': 450, 'protein': 35, 'carbs': 25}
            },
            {
                'name': 'Fried Rice',
                'description': 'Classic fried rice with eggs and vegetables',
                'price': 12.99,
                'category': 'Rice & Noodles',
                'is_featured': False,
                'badges': ['vegetarian'],
                'allergens': ['eggs'],
                'nutritional_info': {'calories': 320, 'protein': 8, 'carbs': 55}
            },
            {
                'name': 'Mango Sticky Rice',
                'description': 'Sweet sticky rice with fresh mango',
                'price': 8.99,
                'category': 'Desserts',
                'is_featured': True,
                'badges': ['vegetarian', 'popular'],
                'allergens': [],
                'nutritional_info': {'calories': 280, 'protein': 4, 'carbs': 55}
            },
            {
                'name': 'Green Tea',
                'description': 'Traditional Japanese green tea',
                'price': 3.99,
                'category': 'Beverages',
                'is_featured': False,
                'badges': ['vegetarian', 'healthy'],
                'allergens': [],
                'nutritional_info': {'calories': 5, 'protein': 0, 'carbs': 1}
            }
        ]
        
        for item_data in menu_items:
            category = created_categories[item_data['category']]
            item, created = MenuItem.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'description': item_data['description'],
                    'price': item_data['price'],
                    'category': category,
                    'is_available': True,
                    'is_featured': item_data['is_featured'],
                    'sort_order': 1,
                    'badges': item_data['badges'],
                    'allergens': item_data['allergens'],
                    'nutritional_info': item_data['nutritional_info']
                }
            )
            if created:
                self.stdout.write(f'Created menu item: {item.name}')

    def create_loyalty_data(self):
        """Create loyalty rewards"""
        self.stdout.write('Creating loyalty data...')
        
        rewards = [
            {
                'name': 'Free Appetizer',
                'description': 'Get a free appetizer with any order',
                'points_required': 500,
                'reward_type': 'free_item',
                'max_redemptions': 100,
                'current_redemptions': 15
            },
            {
                'name': '10% Off Order',
                'description': 'Get 10% off your next order',
                'points_required': 750,
                'reward_type': 'percentage_discount',
                'max_redemptions': 50,
                'current_redemptions': 8
            },
            {
                'name': 'Free Delivery',
                'description': 'Free delivery on your next order',
                'points_required': 300,
                'reward_type': 'free_delivery',
                'max_redemptions': 200,
                'current_redemptions': 25
            }
        ]
        
        for reward_data in rewards:
            reward, created = Reward.objects.get_or_create(
                name=reward_data['name'],
                defaults={
                    'description': reward_data['description'],
                    'points_required': reward_data['points_required'],
                    'reward_type': reward_data['reward_type'],
                    'max_redemptions': reward_data['max_redemptions'],
                    'current_redemptions': reward_data['current_redemptions'],
                    'is_active': True,
                    'valid_from': timezone.now()
                }
            )
            if created:
                self.stdout.write(f'Created reward: {reward.name}')

    def create_promotions_data(self):
        """Create promotions"""
        self.stdout.write('Creating promotions data...')
        
        promotions = [
            {
                'code': 'WELCOME10',
                'name': 'Welcome Discount',
                'description': '10% off your first order',
                'discount_type': 'percentage',
                'discount_value': 10.00,
                'minimum_order_amount': 20.00,
                'maximum_discount': 10.00,
                'usage_limit': 100,
                'current_usage': 25
            },
            {
                'code': 'FREEDEL',
                'name': 'Free Delivery',
                'description': 'Free delivery on any order',
                'discount_type': 'fixed',
                'discount_value': 5.00,
                'minimum_order_amount': 30.00,
                'maximum_discount': 5.00,
                'usage_limit': 200,
                'current_usage': 45
            }
        ]
        
        for promo_data in promotions:
            promotion, created = PromoCode.objects.get_or_create(
                code=promo_data['code'],
                defaults={
                    'description': promo_data['description'],
                    'discount_type': promo_data['discount_type'],
                    'discount_value': promo_data['discount_value'],
                    'minimum_order_amount': promo_data['minimum_order_amount'],
                    'maximum_discount': promo_data['maximum_discount'],
                    'usage_limit': promo_data['usage_limit'],
                    'current_usage': promo_data['current_usage'],
                    'is_active': True,
                    'valid_from': timezone.now()
                }
            )
            if created:
                self.stdout.write(f'Created promotion: {promotion.code}')

    # def create_system_settings(self):
    #     """Create system settings"""
    #     self.stdout.write('Creating system settings...')
    #     
    #     settings = [
    #         {'key': 'delivery_fee', 'value': '5.00', 'description': 'Standard delivery fee in NGN'},
    #         {'key': 'minimum_order', 'value': '20.00', 'description': 'Minimum order amount for delivery'},
    #         {'key': 'points_per_naira', 'value': '12', 'description': 'Points earned per NGN spent'},
    #         {'key': 'tax_rate', 'value': '10', 'description': 'Tax rate as percentage'},
    #     ]
    #     
    #     for setting_data in settings:
    #         setting, created = SystemSetting.objects.get_or_create(
    #             key=setting_data['key'],
    #             defaults={
    #                 'value': setting_data['value'],
    #                 'description': setting_data['description']
    #             }
    #         )
    #         if created:
    #                 self.stdout.write(f'Created setting: {setting.key}')

    def create_addresses(self):
        """Create sample addresses for existing users"""
        self.stdout.write('Creating addresses...')
        
        # Get existing users
        users = User.objects.filter(is_staff=False)[:3]  # Get first 3 non-staff users
        
        addresses = [
            {
                'full_name': 'Test User',
                'address': '123 Main Street',
                'city': 'Abuja',
                'state': 'FCT',
                'postal_code': '900001',
                'country': 'Nigeria',
                'phone': '+2348012345678',
                'is_default': True
            },
            {
                'full_name': 'John Doe',
                'address': '789 Pine Road',
                'city': 'Kano',
                'state': 'Kano',
                'postal_code': '700001',
                'country': 'Nigeria',
                'phone': '+2348098765432',
                'is_default': True
            },
            {
                'full_name': 'Jane Smith',
                'address': '321 Elm Street',
                'city': 'Port Harcourt',
                'state': 'Rivers',
                'postal_code': '500001',
                'country': 'Nigeria',
                'phone': '+2348055555555',
                'is_default': True
            }
        ]
        
        for i, user in enumerate(users):
            if i < len(addresses):
                address_data = addresses[i]
                address, created = Address.objects.get_or_create(
                    user=user,
                    address=address_data['address'],
                    defaults=address_data
                )
                if created:
                    self.stdout.write(f'Created address for {user.username}')
