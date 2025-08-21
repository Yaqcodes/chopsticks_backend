from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from menu.models import Category, MenuItem
from core.models import RestaurantSettings
from loyalty.models import Reward, UserPoints
from promotions.models import PromoCode

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create restaurant settings
        self.create_restaurant_settings()
        
        # Create menu categories
        categories = self.create_menu_categories()
        
        # Create menu items
        self.create_menu_items(categories)
        
        # Create rewards
        self.create_rewards()
        
        # Create promotional codes
        self.create_promo_codes()
        
        # Create sample users
        self.create_sample_users()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )

    def create_restaurant_settings(self):
        """Create restaurant settings."""
        settings, created = RestaurantSettings.objects.get_or_create(
            pk=1,
            defaults={
                'name': 'Chopsticks and Bowls',
                'description': 'Authentic Korean cuisine in Abuja',
                'address': '123 Wuse Zone 2, Abuja, Nigeria',
                'phone': '+234 801 234 5678',
                'email': 'info@chopsticksandbowls.com',
                'website': 'https://chopsticksandbowls.com',
                'opening_time': datetime.strptime('10:00', '%H:%M').time(),
                'closing_time': datetime.strptime('22:00', '%H:%M').time(),
                'is_open': True,
                'delivery_radius_km': Decimal('10.00'),
                'minimum_order_amount': Decimal('5.00'),
                'free_delivery_threshold': Decimal('50.00'),
                'accepts_cash': True,
                'accepts_card': True,
                'accepts_mobile_money': True,
                'facebook_url': 'https://facebook.com/chopsticksandbowls',
                'instagram_url': 'https://instagram.com/chopsticksandbowls',
                'twitter_url': 'https://twitter.com/chopsticksandbowls',
            }
        )
        
        if created:
            self.stdout.write('Created restaurant settings')
        else:
            self.stdout.write('Restaurant settings already exist')

    def create_menu_categories(self):
        """Create menu categories."""
        categories_data = [
            {
                'name': 'Soups',
                'description': 'Warm and comforting Korean soups',
                'sort_order': 1
            },
            {
                'name': 'Noodles',
                'description': 'Delicious Korean noodle dishes',
                'sort_order': 2
            },
            {
                'name': 'Rice Dishes',
                'description': 'Traditional Korean rice-based meals',
                'sort_order': 3
            },
            {
                'name': 'Dumplings',
                'description': 'Handcrafted Korean dumplings',
                'sort_order': 4
            },
            {
                'name': 'Side Dishes',
                'description': 'Perfect accompaniments to your meal',
                'sort_order': 5
            },
            {
                'name': 'Beverages',
                'description': 'Refreshing drinks and traditional teas',
                'sort_order': 6
            }
        ]
        
        categories = []
        for data in categories_data:
            category, created = Category.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        return categories

    def create_menu_items(self, categories):
        """Create menu items."""
        menu_items_data = [
            # Soups
            {
                'name': 'Kimchi Jjigae',
                'description': 'Spicy kimchi stew with pork and tofu',
                'price': Decimal('15.00'),
                'category': categories[0],
                'badges': ['spicy', 'popular'],
                'is_featured': True,
                'sort_order': 1
            },
            {
                'name': 'Doenjang Jjigae',
                'description': 'Traditional soybean paste stew with vegetables',
                'price': Decimal('12.00'),
                'category': categories[0],
                'badges': ['vegetarian'],
                'sort_order': 2
            },
            {
                'name': 'Samgyetang',
                'description': 'Ginseng chicken soup with rice',
                'price': Decimal('18.00'),
                'category': categories[0],
                'badges': ['chef_special'],
                'is_featured': True,
                'sort_order': 3
            },
            
            # Noodles
            {
                'name': 'Japchae',
                'description': 'Stir-fried glass noodles with vegetables and beef',
                'price': Decimal('16.00'),
                'category': categories[1],
                'badges': ['popular'],
                'is_featured': True,
                'sort_order': 1
            },
            {
                'name': 'Bibim Guksu',
                'description': 'Cold spicy noodles with vegetables',
                'price': Decimal('14.00'),
                'category': categories[1],
                'badges': ['spicy', 'cold'],
                'sort_order': 2
            },
            {
                'name': 'Jjajangmyeon',
                'description': 'Black bean sauce noodles with pork',
                'price': Decimal('15.00'),
                'category': categories[1],
                'badges': ['popular'],
                'sort_order': 3
            },
            
            # Rice Dishes
            {
                'name': 'Bibimbap',
                'description': 'Mixed rice bowl with vegetables and egg',
                'price': Decimal('17.00'),
                'category': categories[2],
                'badges': ['popular', 'vegetarian'],
                'is_featured': True,
                'sort_order': 1
            },
            {
                'name': 'Bulgogi',
                'description': 'Marinated beef with rice and side dishes',
                'price': Decimal('20.00'),
                'category': categories[2],
                'badges': ['popular', 'chef_special'],
                'is_featured': True,
                'sort_order': 2
            },
            {
                'name': 'Galbi',
                'description': 'Grilled short ribs with rice',
                'price': Decimal('25.00'),
                'category': categories[2],
                'badges': ['chef_special'],
                'sort_order': 3
            },
            
            # Dumplings
            {
                'name': 'Mandu',
                'description': 'Steamed dumplings with pork and vegetables',
                'price': Decimal('8.00'),
                'category': categories[3],
                'badges': ['popular'],
                'sort_order': 1
            },
            {
                'name': 'Kimchi Mandu',
                'description': 'Spicy kimchi dumplings',
                'price': Decimal('9.00'),
                'category': categories[3],
                'badges': ['spicy'],
                'sort_order': 2
            },
            
            # Side Dishes
            {
                'name': 'Kimchi',
                'description': 'Traditional fermented cabbage',
                'price': Decimal('3.00'),
                'category': categories[4],
                'badges': ['spicy'],
                'sort_order': 1
            },
            {
                'name': 'Banchan Set',
                'description': 'Assorted Korean side dishes',
                'price': Decimal('5.00'),
                'category': categories[4],
                'badges': ['vegetarian'],
                'sort_order': 2
            },
            
            # Beverages
            {
                'name': 'Makgeolli',
                'description': 'Traditional Korean rice wine',
                'price': Decimal('6.00'),
                'category': categories[5],
                'badges': ['new'],
                'sort_order': 1
            },
            {
                'name': 'Barley Tea',
                'description': 'Refreshing Korean barley tea',
                'price': Decimal('2.00'),
                'category': categories[5],
                'badges': ['vegetarian'],
                'sort_order': 2
            }
        ]
        
        for data in menu_items_data:
            menu_item, created = MenuItem.objects.get_or_create(
                name=data['name'],
                category=data['category'],
                defaults=data
            )
            if created:
                self.stdout.write(f'Created menu item: {menu_item.name}')

    def create_rewards(self):
        """Create loyalty rewards."""
        rewards_data = [
            {
                'name': '10% Off Next Order',
                'description': 'Get 10% off your next order',
                'reward_type': 'discount',
                'points_required': 100,
                'discount_percentage': Decimal('10.00'),
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=365),
                'max_redemptions': 0
            },
            {
                'name': 'Free Delivery',
                'description': 'Free delivery on your next order',
                'reward_type': 'free_delivery',
                'points_required': 50,
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=365),
                'max_redemptions': 0
            },
            {
                'name': '$5 Off',
                'description': 'Get $5 off your next order',
                'reward_type': 'discount',
                'points_required': 200,
                'discount_amount': Decimal('5.00'),
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=365),
                'max_redemptions': 0
            }
        ]
        
        for data in rewards_data:
            reward, created = Reward.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'Created reward: {reward.name}')

    def create_promo_codes(self):
        """Create promotional codes."""
        promo_codes_data = [
            {
                'code': 'WELCOME10',
                'description': '10% off for new customers',
                'discount_type': 'percentage',
                'discount_value': Decimal('10.00'),
                'minimum_order_amount': Decimal('20.00'),
                'usage_limit': 100,
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=30)
            },
            {
                'code': 'FREEDEL',
                'description': 'Free delivery on orders over $30',
                'discount_type': 'fixed',
                'discount_value': Decimal('5.00'),
                'minimum_order_amount': Decimal('30.00'),
                'usage_limit': 50,
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=60)
            }
        ]
        
        for data in promo_codes_data:
            promo_code, created = PromoCode.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            if created:
                self.stdout.write(f'Created promo code: {promo_code.code}')

    def create_sample_users(self):
        """Create sample users for testing."""
        users_data = [
            {
                'email': 'customer@example.com',
                'username': 'customer',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+234 801 234 5678',
                'password': 'testpass123'
            },
            {
                'email': 'customer2@example.com',
                'username': 'customer2',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone': '+234 801 234 5679',
                'password': 'testpass123'
            }
        ]
        
        for data in users_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'username': data['username'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'phone': data['phone']
                }
            )
            
            if created:
                user.set_password(data['password'])
                user.save()
                
                # Create user points
                UserPoints.objects.create(user=user)
                
                self.stdout.write(f'Created user: {user.email}')
            else:
                self.stdout.write(f'User already exists: {user.email}')
