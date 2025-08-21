from django.core.management.base import BaseCommand
from core.models import RestaurantSettings
from django.conf import settings


class Command(BaseCommand):
    help = 'Setup RestaurantSettings singleton with default values'

    def handle(self, *args, **options):
        try:
            # Get or create restaurant settings
            settings, created = RestaurantSettings.objects.get_or_create(
                id=1,
                defaults={
                    'name': "Chopsticks and Bowls",
                    'address': "Abuja, Nigeria",
                    'phone': "+234",
                    'email': "info@chopsticksandbowls.com",
                    'opening_hours': {},
                    'delivery_radius': 10.00,
                    'minimum_order': 0.00,
                    'vat_rate': settings.DEFAULT_TAX_RATE,
                    'pickup_delivery_fee': 0.00,
                    'delivery_fee_base': 2000.00,
                    'delivery_fee_per_km': 200.00,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created RestaurantSettings with ID {settings.id}'
                    )
                )
            else:
                # Update existing settings with new fields if they don't have them
                updated = False
                
                if not hasattr(settings, 'vat_rate') or settings.vat_rate is None:
                    settings.vat_rate = 0.075
                    updated = True
                
                if not hasattr(settings, 'pickup_delivery_fee') or settings.pickup_delivery_fee is None:
                    settings.pickup_delivery_fee = 0.00
                    updated = True
                
                if not hasattr(settings, 'delivery_fee_base') or settings.delivery_fee_base is None:
                    settings.delivery_fee_base = 500.00
                    updated = True
                
                if not hasattr(settings, 'delivery_fee_per_km') or settings.delivery_fee_per_km is None:
                    settings.delivery_fee_per_km = 100.00
                    updated = True
                
                if updated:
                    settings.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully updated RestaurantSettings with ID {settings.id}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'RestaurantSettings with ID {settings.id} already exists and is up to date'
                        )
                    )
            
            # Display current settings
            self.stdout.write('\nCurrent Restaurant Settings:')
            self.stdout.write(f'Name: {settings.name}')
            self.stdout.write(f'Address: {settings.address}')
            self.stdout.write(f'Phone: {settings.phone}')
            self.stdout.write(f'Email: {settings.email}')
            self.stdout.write(f'VAT Rate: {settings.vat_rate * 100}%')
            self.stdout.write(f'Pickup Fee: ₦{settings.pickup_delivery_fee}')
            self.stdout.write(f'Base Delivery Fee: ₦{settings.delivery_fee_base}')
            self.stdout.write(f'Delivery Fee per KM: ₦{settings.delivery_fee_per_km}')
            self.stdout.write(f'Delivery Radius: {settings.delivery_radius} km')
            self.stdout.write(f'Minimum Order: ₦{settings.minimum_order}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to setup RestaurantSettings: {str(e)}')
            )
