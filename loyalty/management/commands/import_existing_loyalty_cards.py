from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from loyalty.models import LoyaltyCard
import csv
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Import existing loyalty cards with customer IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Path to CSV file with customer_id,email columns',
        )
        parser.add_argument(
            '--customer-id',
            type=int,
            help='Customer ID number',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='User email for the customer ID',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all existing loyalty cards',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_loyalty_cards()
            return

        if options['csv_file']:
            self.import_from_csv(options['csv_file'])
        elif options['customer_id'] and options['email']:
            self.import_single_card(options['customer_id'], options['email'])
        else:
            self.stdout.write(
                self.style.ERROR('Please provide --csv-file or both --customer-id and --email')
            )

    def import_from_csv(self, csv_file_path):
        """Import loyalty cards from CSV file."""
        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f'CSV file not found: {csv_file_path}')
            )
            return

        created_count = 0
        updated_count = 0
        error_count = 0

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    customer_id = row.get('customer_id', '').strip()
                    email = row.get('email', '').strip()
                    
                    if not customer_id or not email:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping row with missing data: {row}')
                        )
                        error_count += 1
                        continue

                    # Find or create user
                    user, user_created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': email,
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                        }
                    )

                    # Create or update loyalty card
                    loyalty_card, card_created = LoyaltyCard.objects.get_or_create(
                        qr_code=customer_id,
                        defaults={
                            'user': user,
                            'is_active': True
                        }
                    )

                    if card_created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created loyalty card: Customer ID {customer_id} -> {email}'
                            )
                        )
                    else:
                        # Update existing card if user is different
                        if loyalty_card.user != user:
                            loyalty_card.user = user
                            loyalty_card.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Updated loyalty card: Customer ID {customer_id} -> {email}'
                                )
                            )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {row}: {str(e)}')
                    )
                    error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed: Created {created_count}, Updated {updated_count}, Errors {error_count}'
            )
        )

    def import_single_card(self, customer_id, email):
        """Import a single loyalty card."""
        try:
            # Find or create user
            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                }
            )

            # Create or update loyalty card
            loyalty_card, card_created = LoyaltyCard.objects.get_or_create(
                qr_code=str(customer_id),
                defaults={
                    'user': user,
                    'is_active': True
                }
            )

            if card_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created loyalty card: Customer ID {customer_id} -> {email}'
                    )
                )
            else:
                if loyalty_card.user != user:
                    loyalty_card.user = user
                    loyalty_card.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Updated loyalty card: Customer ID {customer_id} -> {email}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Loyalty card already exists: Customer ID {customer_id} -> {email}'
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating loyalty card: {str(e)}')
            )

    def list_loyalty_cards(self):
        """List all existing loyalty cards."""
        loyalty_cards = LoyaltyCard.objects.all().select_related('user')
        
        if not loyalty_cards:
            self.stdout.write('No loyalty cards found.')
            return

        self.stdout.write(f'Found {loyalty_cards.count()} loyalty cards:')
        self.stdout.write('-' * 80)
        
        for card in loyalty_cards:
            status = 'ACTIVE' if card.is_active else 'INACTIVE'
            last_scan = card.last_scan.strftime('%Y-%m-%d %H:%M:%S') if card.last_scan else 'Never'
            user_email = card.user.email if card.user else 'Unassigned'
            
            self.stdout.write(
                f'Customer ID: {card.qr_code} | '
                f'User: {user_email} | '
                f'Status: {status} | '
                f'Last Scan: {last_scan}'
            )
