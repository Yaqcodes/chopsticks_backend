from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import RestaurantSettings
from menu.models import Category


class Command(BaseCommand):
    help = "Seed Zmall apparel categories (from zmall-frontend mockData)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print actions without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *_args, **options):
        dry_run = options["dry_run"]

        zmall = RestaurantSettings.objects.filter(domain__icontains='zmall').first()
        if not zmall and not dry_run:
            self.stderr.write(self.style.ERROR("Zmall tenant not found. Create RestaurantSettings with domain containing 'zmall'."))
            return

        categories = [
            {"name": "Pants", "slug": "pants", "sort_order": 1},
            {"name": "Shoes", "slug": "shoes", "sort_order": 2},
            {"name": "Sandals | Espadrilles", "slug": "sandals", "sort_order": 3},
            {"name": "Bags", "slug": "bags", "sort_order": 4},
            {"name": "Accessories", "slug": "accessories", "sort_order": 5},
            {"name": "Dresses", "slug": "dresses", "sort_order": 6},
            {"name": "Shirts", "slug": "shirts", "sort_order": 7},
        ]

        created = 0
        updated = 0

        for c in categories:
            name = c["name"]
            slug = (c.get("slug") or "").lower()[:100]

            if dry_run:
                self.stdout.write(f"[dry-run] ensure Category slug={slug!r} name={name!r} for Zmall")
                continue

            _, was_created = Category.objects.update_or_create(
                restaurant_settings=zmall,
                slug=slug,
                defaults={
                    "name": name,
                    "description": "",
                    "is_active": True,
                    "sort_order": c.get("sort_order", 0),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        if dry_run:
            return

        self.stdout.write(self.style.SUCCESS(f"Zmall categories seeded. Created={created}, Updated={updated}"))
