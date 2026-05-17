from django.db import migrations, models

from menu.size_grids import SIZE_GRID_CHOICES, SIZE_GRID_NONE


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
                choices=SIZE_GRID_CHOICES,
                default=SIZE_GRID_NONE,
                help_text=(
                    'Storefront fixed size row for this category. Leave blank for flexible sizes '
                    '(perfume volume, ONE SIZE, etc.).'
                ),
                max_length=32,
            ),
        ),
    ]
