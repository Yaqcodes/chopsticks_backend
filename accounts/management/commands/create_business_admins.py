"""
Management command to create business admin users.

Creates admin users for Roschi Water and Chopsticks & Bowls businesses.
"""

from django.core.management.base import BaseCommand
from accounts.models import User
from core.models import RestaurantSettings


class Command(BaseCommand):
    help = 'Create admin users for Roschi Water and Chopsticks & Bowls businesses'

    def handle(self, *args, **options):
        # Get or create businesses
        roschi_settings = RestaurantSettings.objects.filter(
            domain__icontains='roschi'
        ).first()
        
        if not roschi_settings:
            roschi_settings = RestaurantSettings.objects.filter(
                name__icontains='Roschi'
            ).first()
        
        chopsticks_settings = RestaurantSettings.objects.filter(
            domain__icontains='chopsticks'
        ).first()
        
        if not chopsticks_settings:
            chopsticks_settings = RestaurantSettings.objects.filter(
                name__icontains='Chopsticks'
            ).first()
        
        # Create Roschi admin
        roschi_admin, created = User.objects.get_or_create(
            email='admin@roschiwater.com',
            defaults={
                'username': 'roschi_admin',
                'first_name': 'Roschi',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': False,
            }
        )
        
        if created:
            roschi_admin.set_password('Password$')
            roschi_admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created Roschi admin: {roschi_admin.email}')
            )
        else:
            roschi_admin.set_password('Password$')
            roschi_admin.save()
            self.stdout.write(
                self.style.WARNING(f'⚠ Updated Roschi admin password: {roschi_admin.email}')
            )
        
        # Link Roschi admin to Roschi business
        if roschi_settings:
            roschi_admin.businesses.add(roschi_settings)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Linked Roschi admin to business: {roschi_settings.name}')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ Roschi business settings not found. Please create it first.')
            )
        
        # Create Chopsticks admin
        cb_admin, created = User.objects.get_or_create(
            email='admin@chopsticksandbowls.com',
            defaults={
                'username': 'cb_admin',
                'first_name': 'Chopsticks',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': False,
            }
        )
        
        if created:
            cb_admin.set_password('Password$')
            cb_admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created Chopsticks admin: {cb_admin.email}')
            )
        else:
            cb_admin.set_password('Password$')
            cb_admin.save()
            self.stdout.write(
                self.style.WARNING(f'⚠ Updated Chopsticks admin password: {cb_admin.email}')
            )
        
        # Link Chopsticks admin to Chopsticks business
        if chopsticks_settings:
            cb_admin.businesses.add(chopsticks_settings)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Linked Chopsticks admin to business: {chopsticks_settings.name}')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ Chopsticks business settings not found. Please create it first.')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ Business admin users created successfully!')
        )
        self.stdout.write('\nLogin credentials:')
        self.stdout.write(f'  Roschi Admin: admin@roschiwater.com / Password$')
        self.stdout.write(f'  CB Admin: admin@chopsticksandbowls.com / Password$')
