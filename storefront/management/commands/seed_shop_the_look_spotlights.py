"""
Seed Zmall shop_the_look spotlight posts (metadata + product links).

Expects lifestyle images already on the server under MEDIA_ROOT/spotlights/
(default). Does not read from the frontend repo or copy files.
"""

from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import CatalogListingMode, RestaurantSettings
from menu.models import MenuItem, Product
from storefront.models import SpotlightPlacement, SpotlightPost, SpotlightPostLink

DEFAULT_MEDIA_SUBDIR = 'spotlights'

# Canonical shop-the-look rows (image filename must exist under the images directory).
SHOP_THE_LOOK_POSTS = [
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
    help = (
        'Seed shop_the_look spotlight posts for Zmall using images already in '
        f'MEDIA_ROOT/{DEFAULT_MEDIA_SUBDIR}/ (or --images-dir).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without writing to the database.',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete existing Zmall shop_the_look spotlight posts before seeding.',
        )
        parser.add_argument(
            '--images-dir',
            type=str,
            default='',
            help=(
                f'Directory containing spotlight image files '
                f'(default: {{MEDIA_ROOT}}/{DEFAULT_MEDIA_SUBDIR}/).'
            ),
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

        images_dir = self._images_dir(options['images_dir'])
        if not images_dir.is_dir():
            self.stderr.write(
                self.style.ERROR(
                    f'Images directory not found: {images_dir}\n'
                    f'Upload files to MEDIA_ROOT/{DEFAULT_MEDIA_SUBDIR}/ on this server, '
                    'or pass --images-dir.'
                )
            )
            return

        file_index = self._build_file_index(images_dir)
        media_subdir = self._media_subdir_for_dir(images_dir)

        if replace and not dry_run:
            deleted, _ = SpotlightPost.objects.filter(
                restaurant_settings=zmall,
                placement=SpotlightPlacement.SHOP_THE_LOOK,
            ).delete()
            self.stdout.write(f'Removed {deleted} existing shop_the_look spotlight row(s).')

        created_posts = 0
        created_links = 0
        skipped_links = 0
        missing_images = 0

        with transaction.atomic():
            for row in SHOP_THE_LOOK_POSTS:
                image_path = self._resolve_image_path(file_index, row['image'])
                if image_path is None:
                    missing_images += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"Missing image '{row['image']}' in {images_dir}"
                        )
                    )
                    continue

                product_ids = self._resolve_product_ids(zmall, row['product_ids'])
                if not product_ids:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Post sort_order={row['sort_order']}: no catalog products resolved "
                            f"from ids {row['product_ids']}."
                        )
                    )

                rel_name = f'{media_subdir}/{image_path.name}'.replace('\\', '/')

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] sort_order={row['sort_order']} image={rel_name} "
                        f"products={product_ids}"
                    )
                    continue

                post = SpotlightPost.objects.create(
                    restaurant_settings=zmall,
                    external_url=row['external_url'],
                    cta_label='Shop the look',
                    placement=SpotlightPlacement.SHOP_THE_LOOK,
                    sort_order=row['sort_order'],
                    is_active=True,
                )
                post.image.name = rel_name
                post.save(update_fields=['image'])
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
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {created_posts} spotlight post(s), {created_links} product link(s) '
                f'(images from {images_dir}).'
            )
        )
        if missing_images:
            self.stdout.write(self.style.ERROR(f'{missing_images} post(s) skipped (missing images).'))
        if skipped_links:
            self.stdout.write(
                self.style.WARNING(
                    f'{skipped_links} static product id(s) could not be resolved to Products.'
                )
            )

    def _images_dir(self, override: str) -> Path:
        if override:
            return Path(override).expanduser().resolve()
        return (Path(settings.MEDIA_ROOT) / DEFAULT_MEDIA_SUBDIR).resolve()

    def _media_subdir_for_dir(self, images_dir: Path) -> str:
        """Relative path under MEDIA_ROOT for ImageField.name (e.g. storefront)."""
        media_root = Path(settings.MEDIA_ROOT).resolve()
        try:
            rel = images_dir.relative_to(media_root)
            return str(rel).replace('\\', '/')
        except ValueError:
            return DEFAULT_MEDIA_SUBDIR

    def _build_file_index(self, images_dir: Path) -> dict[str, Path]:
        index = {}
        for path in images_dir.iterdir():
            if path.is_file():
                index[path.name.lower()] = path
        return index

    def _resolve_image_path(self, file_index, filename: str) -> Optional[Path]:
        return file_index.get(filename.lower())

    def _resolve_product_ids(self, zmall, raw_ids):
        resolved = []
        seen = set()
        for raw_id in raw_ids:
            product_id = self._resolve_one_product_id(zmall, raw_id)
            if product_id and product_id not in seen:
                seen.add(product_id)
                resolved.append(product_id)
        return resolved

    def _resolve_one_product_id(self, zmall, raw_id):
        product = Product.objects.filter(id=raw_id, restaurant_settings=zmall).first()
        if product:
            return product.id

        menu_item = MenuItem.objects.filter(
            id=raw_id,
            restaurant_settings=zmall,
        ).select_related('product').first()
        if menu_item and menu_item.product_id:
            return menu_item.product_id

        return None
