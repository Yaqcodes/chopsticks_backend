"""
Step 3: Drop the legacy size_grid_legacy CharField — data is now in SizeGrid FK.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0027_seed_size_grids'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='size_grid_legacy',
        ),
    ]
