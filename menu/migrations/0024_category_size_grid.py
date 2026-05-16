from django.db import migrations, models

from menu.size_grids import (
    DEFAULT_SIZE_GRID_BY_CATEGORY_SLUG,
    SIZE_GRID_CHOICES,
    SIZE_GRID_NONE,
)


def backfill_category_size_grid(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all():
        slug = (cat.slug or '').lower()
        grid = DEFAULT_SIZE_GRID_BY_CATEGORY_SLUG.get(slug, SIZE_GRID_NONE)
        if grid and cat.size_grid != grid:
            cat.size_grid = grid
            cat.save(update_fields=['size_grid'])


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0023_category_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='size_grid',
            field=models.CharField(
                blank=True,
                choices=SIZE_GRID_CHOICES,
                default=SIZE_GRID_NONE,
                help_text=(
                    'Storefront fixed size row for this category. Leave blank for flexible sizes '
                    '(perfume volume, ONE SIZE, etc.).'
                ),
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill_category_size_grid, migrations.RunPython.noop),
    ]
