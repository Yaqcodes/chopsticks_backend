from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from loyalty.models import LoyaltyCard, UserPoints
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a test user and assign a loyalty card for QR scanner testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='test@example.com',
            help='Email for test user (default: test@example.com)'
        )
        parser.add_argument(
            '--qr-code',
            type=str,
            default='123',
            help='QR code to assign (default: 123)'
        )

    def handle(self, *args, **options):
        email = options['email']
        qr_code = options['qr_code']

        self.stdout.write(
            self.style.SUCCESS(
                f'Setting up test user with email: {email} and QR code: {qr_code}'
            )
        )

        with transaction.atomic():
            # Create test user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': 'Test',
                    'last_name': 'User',
                    'is_active': True
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created new test user: {email}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Test user already exists: {email}')
                )

            # Create user points
            user_points, created = UserPoints.objects.get_or_create(user=user)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created user points for: {email}')
                )

            # Find and assign loyalty card
            try:
                loyalty_card = LoyaltyCard.objects.get(qr_code=qr_code)
                
                if loyalty_card.user:
                    self.stdout.write(
                        self.style.WARNING(
                            f'QR code {qr_code} is already assigned to {loyalty_card.user.email}'
                        )
                    )
                else:
                    # Assign the card to the test user
                    loyalty_card.user = user
                    loyalty_card.is_active = True
                    loyalty_card.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully assigned QR code {qr_code} to {email}'
                        )
                    )

            except LoyaltyCard.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'QR code {qr_code} not found in database')
                )
                return

        # Display test information
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS('🎯 QR SCANNER TEST SETUP COMPLETE')
        )
        self.stdout.write('='*50)
        self.stdout.write(f'Test User Email: {email}')
        self.stdout.write(f'QR Code: {qr_code}')
        self.stdout.write(f'User Points Balance: {user_points.balance}')
        self.stdout.write('\n📱 To test the QR scanner:')
        self.stdout.write('1. Go to: http://127.0.0.1:8000/admin-qr/qr-scan-interface/')
        self.stdout.write('2. Enter QR Code: ' + qr_code)
        self.stdout.write('3. Enter Visit Amount: 25.00 (optional)')
        self.stdout.write('4. Click "Scan QR Code"')
        self.stdout.write('\n✅ The scanner should award points and show success message!')

