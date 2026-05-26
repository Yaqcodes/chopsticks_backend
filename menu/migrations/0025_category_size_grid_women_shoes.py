from django.db import migrations, models

_SIZE_GRID_NONE = ''

_SIZE_GRID_CHOICES = [
    ('', 'Flexible (sizes from variants only)'),
    ('shoe_eu', 'Shoes — EU 40–47 (men)'),
    ('shoe_eu_women', 'Shoes — EU 37–42 (women)'),
    ('clothing_s_xl', 'Apparel — S, M, L, XL'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0024_category_size_grid'),
    ]

    operations = [
        migrations.AlterField(
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
    ]
