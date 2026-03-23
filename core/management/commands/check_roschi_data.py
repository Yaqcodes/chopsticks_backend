from django.core.management.base import BaseCommand
from core.models import RestaurantSettings
from menu.models import MenuItem, Category
from orders.models import Order, OrderItem
from payments.models import Payment


class Command(BaseCommand):
    help = 'Check if Roschi Water data exists and is properly linked'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Checking Roschi Water Data...'))
        self.stdout.write('='*60 + '\n')
        
        # Check RestaurantSettings
        self.stdout.write('1. RestaurantSettings:')
        all_settings = RestaurantSettings.objects.all()
        self.stdout.write(f'   Total RestaurantSettings: {all_settings.count()}')
        
        for settings in all_settings:
            self.stdout.write(f'   - {settings.name} (domain: {settings.domain or "None"})')
        
        roschi_settings = RestaurantSettings.objects.filter(domain='roschiwater.com').first()
        if roschi_settings:
            self.stdout.write(self.style.SUCCESS(f'   ✓ Found Roschi Settings: {roschi_settings.name}'))
        else:
            self.stdout.write(self.style.WARNING('   ✗ No RestaurantSettings with domain="roschiwater.com"'))
            # Check if there's one with Roschi in the name
            roschi_by_name = RestaurantSettings.objects.filter(name__icontains='Roschi').first()
            if roschi_by_name:
                self.stdout.write(self.style.WARNING(f'   Found settings with "Roschi" in name: {roschi_by_name.name} (domain: {roschi_by_name.domain})'))
        
        # Check MenuItems
        self.stdout.write('\n2. MenuItems:')
        all_items = MenuItem.objects.all()
        self.stdout.write(f'   Total MenuItems: {all_items.count()}')
        
        if roschi_settings:
            roschi_items = MenuItem.objects.filter(restaurant_settings=roschi_settings)
            self.stdout.write(f'   MenuItems linked to Roschi: {roschi_items.count()}')
            if roschi_items.exists():
                for item in roschi_items[:5]:
                    self.stdout.write(f'   - {item.name} ({item.category.name})')
        else:
            # Check all items and their settings
            for item in all_items[:5]:
                settings_name = item.restaurant_settings.name if item.restaurant_settings else 'None'
                settings_domain = item.restaurant_settings.domain if item.restaurant_settings else 'None'
                self.stdout.write(f'   - {item.name} (Settings: {settings_name}, Domain: {settings_domain})')
        
        # Check Categories
        self.stdout.write('\n3. Categories:')
        all_categories = Category.objects.all()
        self.stdout.write(f'   Total Categories: {all_categories.count()}')
        if roschi_settings:
            # Categories that have Roschi items
            roschi_categories = Category.objects.filter(menu_items__restaurant_settings=roschi_settings).distinct()
            self.stdout.write(f'   Categories with Roschi items: {roschi_categories.count()}')
        
        # Check Orders
        self.stdout.write('\n4. Orders:')
        all_orders = Order.objects.all()
        self.stdout.write(f'   Total Orders: {all_orders.count()}')
        if roschi_settings:
            roschi_orders = Order.objects.filter(restaurant_settings=roschi_settings)
            self.stdout.write(f'   Orders linked to Roschi: {roschi_orders.count()}')
        else:
            for order in all_orders[:3]:
                settings_name = order.restaurant_settings.name if order.restaurant_settings else 'None'
                settings_domain = order.restaurant_settings.domain if order.restaurant_settings else 'None'
                self.stdout.write(f'   - Order {order.order_number} (Settings: {settings_name}, Domain: {settings_domain})')
        
        # Check Payments
        self.stdout.write('\n5. Payments:')
        all_payments = Payment.objects.all()
        self.stdout.write(f'   Total Payments: {all_payments.count()}')
        if roschi_settings:
            roschi_payments = Payment.objects.filter(order__restaurant_settings=roschi_settings)
            self.stdout.write(f'   Payments linked to Roschi: {roschi_payments.count()}')
        
        # Recommendations
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Recommendations:'))
        self.stdout.write('='*60)
        
        if not roschi_settings:
            self.stdout.write(self.style.WARNING('1. Run: python manage.py populate_roschi_settings'))
            self.stdout.write(self.style.WARNING('   This will create/update Roschi Water settings with domain="roschiwater.com"'))
        
        if roschi_settings and all_items.exists() and not MenuItem.objects.filter(restaurant_settings=roschi_settings).exists():
            self.stdout.write(self.style.WARNING('2. Existing MenuItems are not linked to Roschi Settings'))
            self.stdout.write(self.style.WARNING('   You may need to update existing items to link them to Roschi'))
        
        if roschi_settings and all_orders.exists() and not Order.objects.filter(restaurant_settings=roschi_settings).exists():
            self.stdout.write(self.style.WARNING('3. Existing Orders are not linked to Roschi Settings'))
        
        self.stdout.write('='*60 + '\n')
