from django.core.management.base import BaseCommand
from loyalty.models import LoyaltyCard
from django.db import transaction


class Command(BaseCommand):
    help = 'Populate database with 1000 unassigned loyalty cards (QR codes 1-1000)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='Starting number for QR codes (default: 1)'
        )
        parser.add_argument(
            '--end',
            type=int,
            default=1000,
            help='Ending number for QR codes (default: 1000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for database operations (default: 100)'
        )

    def handle(self, *args, **options):
        start = options['start']
        end = options['end']
        batch_size = options['batch_size']

        self.stdout.write(
            self.style.SUCCESS(
                f'Creating loyalty cards from {start} to {end}...'
            )
        )

        # Check for existing cards
        existing_count = LoyaltyCard.objects.filter(
            qr_code__regex=r'^\d+$'
        ).count()
        
        if existing_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_count} existing numeric loyalty cards. '
                    'Skipping existing QR codes...'
                )
            )

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for i in range(start, end + 1):
                qr_code = str(i)
                
                # Check if card already exists
                if LoyaltyCard.objects.filter(qr_code=qr_code).exists():
                    skipped_count += 1
                    continue
                
                # Create the loyalty card
                card = LoyaltyCard.objects.create(
                    qr_code=qr_code,
                    is_active=False,  # Unassigned cards are inactive
                    user=None  # No user assigned
                )
                created_count += 1
                
                # Progress update every batch_size
                if created_count % batch_size == 0:
                    self.stdout.write(
                        f'Created {created_count} cards... (current: {qr_code})'
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} loyalty cards!'
            )
        )
        
        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Skipped {skipped_count} existing cards.'
                )
            )
        
        total_cards = LoyaltyCard.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Total loyalty cards in database: {total_cards}'
            )
        )
