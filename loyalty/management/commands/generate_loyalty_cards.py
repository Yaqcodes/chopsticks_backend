from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from loyalty.models import LoyaltyCard

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate loyalty cards for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate loyalty cards for all users',
        )
        parser.add_argument(
            '--user-ids',
            nargs='+',
            type=int,
            help='Generate loyalty cards for specific user IDs',
        )

    def handle(self, *args, **options):
        if options['all']:
            users = User.objects.all()
        elif options['user_ids']:
            users = User.objects.filter(id__in=options['user_ids'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --all or --user-ids')
            )
            return

        created_count = 0
        existing_count = 0

        for user in users:
            loyalty_card, created = LoyaltyCard.objects.get_or_create(
                user=user,
                defaults={'is_active': True}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created loyalty card for user {user.email} with QR code: {loyalty_card.qr_code}'
                    )
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Loyalty card already exists for user {user.email}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + existing_count} users. '
                f'Created: {created_count}, Existing: {existing_count}'
            )
        )
