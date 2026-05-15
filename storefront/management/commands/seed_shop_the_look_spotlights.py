"""
Seed Zmall shop_the_look spotlight posts from zmall-frontend staticMarketing INSTAGRAM_POSTS.

Copies lifestyle images into MEDIA_ROOT/spotlights/ and links catalog Products
(ids from static data; resolves MenuItem ids to Product when needed).
"""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import CatalogListingMode, RestaurantSettings
from menu.models import MenuItem, Product
from storefront.models import SpotlightPlacement, SpotlightPost, SpotlightPostLink

# Mirrors zmall-frontend/src/data/staticMarketing.js INSTAGRAM_POSTS
STATIC_INSTAGRAM_POSTS = [
    {
        'sort_order': 1,
        'image': 'him_top.jpg',
        'external_url': 'https://www.instagram.com/p/DRU2piCCEXZ/?igsh=MWM4OTdwMjhtNTcydw==',
        'product_ids': [16, 18],
    },
    {
        'sort_order': 2,
        'image': 'him_shoes.jpg',
        'external_url': 'https://www.instagram.com/p/DNP2Dh8omrC/?igsh=cjNwOWN6ejI5Z211',
        'product_ids': [4, 5],
    },
    {
        'sort_order': 3,
        'image': 'her_watch.jpg',
        'external_url': 'https://www.instagram.com/p/DP93mVtCITB/?igsh=a3F1czEyMnE2bHF2',
        'product_ids': [10, 12],
    },
    {
        'sort_order': 4,
        'image': 'her_top.jpg',
        'external_url': 'https://www.instagram.com/p/DNkKuKUILOm/?igsh=M2k1YmlrbDg3cnRq',
        'product_ids': [17, 13],
    },
    {
        'sort_order': 5,
        'image': 'her_shoes.jpg',
        'external_url': 'https://www.instagram.com/p/DQEfyFCiOqb/?igsh=ZTU1dDh6enFzemFn',
        'product_ids': [6],
    },
    {
        'sort_order': 6,
        'image': 'her_watch.jpg',
        'external_url': 'https://www.instagram.com/p/DLkuA0ts0fv/?igsh=cW5scXlxOGQ5YWFl',
        'product_ids': [10, 12],
    },
    {
        'sort_order': 7,
        'image': 'perfume_her.jpg',
        'external_url': 'https://www.instagram.com/p/DQ4gchAiChN/?igsh=c3BueGZ6aG52OHk2',
        'product_ids': [11, 12],
    },
    {
        'sort_order': 8,
        'image': 'perfume.jpg',
        'external_url': 'https://www.instagram.com/p/DQuLt86iEC-/?igsh=MWptMWF4aDM2ZHNydQ==',
        'product_ids': [11, 12],
    },
    {
        'sort_order': 9,
        'image': 'perfume_him.jpg',
        'external_url': 'https://www.instagram.com/p/DQfNgOjiKV7/?igsh=MWx2MmYwZmdhZzAwaA==',
        'product_ids': [10, 12],
    },
    {
        'sort_order': 10,
        'image': 'acc1.jpg',
        'external_url': 'https://www.instagram.com/p/DPd3y7aCFIk/?igsh=azlkZzc5OHlsdHFi',
        'product_ids': [10, 11, 12],
    },
    {
        'sort_order': 11,
        'image': 'acc2.jpg',
        'external_url': 'https://www.instagram.com/p/DMtNvxoM4wF/?igsh=MXB1bGkxNGRoc2R0NA==',
        'product_ids': [10, 11, 12],
    },
    {
        'sort_order': 12,
        'image': 'acc3.jpg',
        'external_url': 'https://www.instagram.com/p/DNIKYnxIMrp/?igsh=MXVrcDg0MDNzbHY4ZQ==',
        'product_ids': [10, 11, 12],
    },
]


class Command(BaseCommand):
    help = 'Seed shop_the_look spotlight posts for Zmall from frontend static INSTAGRAM_POSTS data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without writing to the database or copying files.',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete existing Zmall shop_the_look spotlight posts before seeding.',
        )
        parser.add_argument(
            '--assets-dir',
            type=str,
            default='',
            help='Override path to Instagram Picks folder (default: ../zmall-frontend/src/assets/Instagram Picks).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        replace = options['replace']

        zmall = RestaurantSettings.objects.filter(domain__icontains='zmall').first()
        if not zmall:
            self.stderr.write(self.style.ERROR('Zmall tenant not found (domain containing "zmall").'))
            return

        if zmall.catalog_listing_mode != CatalogListingMode.PRODUCT:
            self.stdout.write(
                self.style.WARNING(
                    f'Tenant catalog_listing_mode is {zmall.catalog_listing_mode!r}; '
                    'expected "product" for Zmall spotlight links.'
                )
            )

        assets_dir = self._assets_dir(options['assets_dir'])
        if not assets_dir.is_dir():
            self.stderr.write(self.style.ERROR(f'Assets directory not found: {assets_dir}'))
            return

        media_spotlights = Path(settings.MEDIA_ROOT) / 'spotlights'
        if not dry_run:
            media_spotlights.mkdir(parents=True, exist_ok=True)

        if replace and not dry_run:
            deleted, _ = SpotlightPost.objects.filter(
                restaurant_settings=zmall,
                placement=SpotlightPlacement.SHOP_THE_LOOK,
            ).delete()
            self.stdout.write(f'Removed {deleted} existing shop_the_look spotlight row(s).')

        created_posts = 0
        created_links = 0
        skipped_links = 0

        with transaction.atomic():
            for row in STATIC_INSTAGRAM_POSTS:
                src = assets_dir / row['image']
                if not src.is_file():
                    self.stderr.write(self.style.ERROR(f'Missing image: {src}'))
                    continue

                product_ids = self._resolve_product_ids(zmall, row['product_ids'])
                if not product_ids:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Post sort_order={row['sort_order']}: no catalog products resolved "
                            f"from ids {row['product_ids']}."
                        )
                    )

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Spotlight sort_order={row['sort_order']} "
                        f"image={src.name} products={product_ids} url={row['external_url'][:50]}..."
                    )
                    continue

                post = SpotlightPost(
                    restaurant_settings=zmall,
                    external_url=row['external_url'],
                    cta_label='Shop the look',
                    placement=SpotlightPlacement.SHOP_THE_LOOK,
                    sort_order=row['sort_order'],
                    is_active=True,
                )
                post.save()

                with src.open('rb') as fh:
                    post.image.save(src.name, File(fh), save=True)

                created_posts += 1

                for link_order, product_id in enumerate(product_ids):
                    SpotlightPostLink.objects.create(
                        spotlight=post,
                        product_id=product_id,
                        sort_order=link_order,
                    )
                    created_links += 1

                skipped_links += max(0, len(row['product_ids']) - len(product_ids))

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete (no changes saved).'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Seeded {created_posts} spotlight post(s), {created_links} product link(s). '
                    f'Images under {media_spotlights}.'
                )
            )
            if skipped_links:
                self.stdout.write(
                    self.style.WARNING(
                        f'{skipped_links} static product id(s) could not be resolved to Products.'
                    )
                )

    def _assets_dir(self, override: str) -> Path:
        if override:
            return Path(override).expanduser().resolve()
        return (
            Path(settings.BASE_DIR).parent
            / 'zmall-frontend'
            / 'src'
            / 'assets'
            / 'Instagram Picks'
        ).resolve()

    def _resolve_product_ids(self, zmall, raw_ids):
        """Map static ids to Product PKs for this tenant (Product id or linked MenuItem)."""
        resolved = []
        seen = set()
        for raw_id in raw_ids:
            product_id = self._resolve_one_product_id(zmall, raw_id)
            if product_id and product_id not in seen:
                seen.add(product_id)
                resolved.append(product_id)
        return resolved

    def _resolve_one_product_id(self, zmall, raw_id):
        product = Product.objects.filter(
            id=raw_id,
            restaurant_settings=zmall,
        ).first()
        if product:
            return product.id

        menu_item = MenuItem.objects.filter(
            id=raw_id,
            restaurant_settings=zmall,
        ).select_related('product').first()
        if menu_item and menu_item.product_id:
            return menu_item.product_id

        return None
