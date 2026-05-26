from django.db import migrations, models

_SIZE_GRID_NONE = ''

_SIZE_GRID_CHOICES = [
    ('', 'Flexible (sizes from variants only)'),
    ('shoe_eu', 'Shoes — EU 40–47 (men)'),
    ('shoe_eu_women', 'Shoes — EU 37–42 (women)'),
    ('clothing_s_xl', 'Apparel — S, M, L, XL'),
]

_DEFAULT_SIZE_GRID_BY_CATEGORY_SLUG = {
    'shoes': 'shoe_eu',
    'pants': 'clothing_s_xl',
    'dresses': 'clothing_s_xl',
    'shirts': 'clothing_s_xl',
}


def backfill_category_size_grid(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all():
        slug = (cat.slug or '').lower()
        grid = _DEFAULT_SIZE_GRID_BY_CATEGORY_SLUG.get(slug, _SIZE_GRID_NONE)
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
                choices=_SIZE_GRID_CHOICES,
                default=_SIZE_GRID_NONE,
                help_text=(
                    'Storefront fixed size row for this category. Leave blank for flexible sizes '
                    '(perfume volume, ONE SIZE, etc.).'
                ),
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill_category_size_grid, migrations.RunPython.noop),
    ]
