from django.core.management.base import BaseCommand
from core.models import RestaurantSettings


class Command(BaseCommand):
    help = 'Populate Roschi Water business settings with correct information'

    def handle(self, *args, **options):
        try:
            # Update or create Roschi Water settings
            # Try multiple possible domains
            domains_to_try = ['roschiwater.com', 'www.roschiwater.com', 'api.roschiwater.com']
            
            roschi_settings = None
            for domain in domains_to_try:
                try:
                    roschi_settings = RestaurantSettings.objects.get(domain=domain)
                    self.stdout.write(
                        self.style.SUCCESS(f'Found existing settings for domain: {domain}')
                    )
                    break
                except RestaurantSettings.DoesNotExist:
                    continue
            
            # If not found, create new one
            if not roschi_settings:
                roschi_settings, created = RestaurantSettings.objects.update_or_create(
                    domain='roschiwater.com',
                    defaults={
                        'name': 'Roschi Water',
                        'description': 'Premium table water and sachet water. Produced and Packaged by Rocy Global Stores.',
                        'tagline': 'Pure by nature, bottled at source—just pure refreshment.',
                        'address': 'Shop No 8, Minfa 1 Garden Estate Shopping Complex, Lokogoma, Abuja, FCT',
                        'phone': '+2348077057423, +2348162797910',
                        'email': 'roschiwaters@gmail.com',
                        'website': 'https://roschiwater.com',
                        'vat_rate': 0.075,
                        'accepts_cash': True,
                        'accepts_card': True,
                        'accepts_mobile_money': True,
                        'is_open': True,
                    },
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS('Created new Roschi Water settings')
                    )
            else:
                # Update existing settings
                roschi_settings.name = 'Roschi Water'
                roschi_settings.description = 'Premium table water and sachet water. Produced and Packaged by Rocy Global Stores.'
                roschi_settings.tagline = 'Pure by nature, bottled at source—just pure refreshment.'
                roschi_settings.address = 'Shop No 8, Minfa 1 Garden Estate Shopping Complex, Lokogoma, Abuja, FCT'
                roschi_settings.phone = '+2348077057423, +2348162797910'
                roschi_settings.email = 'roschiwaters@gmail.com'
                roschi_settings.website = 'https://roschiwater.com'
                
                # Ensure domain is set correctly
                if not roschi_settings.domain:
                    roschi_settings.domain = 'roschiwater.com'
                
                roschi_settings.save()
                self.stdout.write(
                    self.style.SUCCESS('Updated existing Roschi Water settings')
                )
            
            # Display updated settings
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('Roschi Water Business Settings:'))
            self.stdout.write('='*60)
            self.stdout.write(f'Name: {roschi_settings.name}')
            self.stdout.write(f'Domain: {roschi_settings.domain}')
            self.stdout.write(f'Tagline: {roschi_settings.tagline}')
            self.stdout.write(f'Address: {roschi_settings.address}')
            self.stdout.write(f'Phone: {roschi_settings.phone}')
            self.stdout.write(f'Email: {roschi_settings.email}')
            self.stdout.write(f'Website: {roschi_settings.website}')
            self.stdout.write(f'Description: {roschi_settings.description}')
            self.stdout.write('='*60)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to populate Roschi Water settings: {str(e)}')
            )
            raise
