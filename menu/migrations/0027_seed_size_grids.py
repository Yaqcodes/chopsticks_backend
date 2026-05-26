"""
Step 2: Seed SizeGrid rows from legacy CharField values and link categories.
"""
from django.db import migrations

LEGACY_GRIDS = {
    'shoe_eu': {
        'name': "Men's Shoes — EU 40–47",
        'key': 'shoe-eu',
        'sizes': ['40', '41', '42', '43', '44', '45', '46', '47'],
    },
    'shoe_eu_women': {
        'name': "Women's Shoes — EU 37–42",
        'key': 'shoe-eu-women',
        'sizes': ['37', '38', '39', '40', '41', '42'],
    },
    'clothing_s_xl': {
        'name': 'Apparel — S, M, L, XL',
        'key': 'clothing-s-xl',
        'sizes': ['S', 'M', 'L', 'XL'],
    },
}


def seed_and_link(apps, schema_editor):
    SizeGrid = apps.get_model('menu', 'SizeGrid')
    Category = apps.get_model('menu', 'Category')

    rs_ids = set(
        Category.objects.exclude(size_grid_legacy='')
        .exclude(size_grid_legacy__isnull=True)
        .values_list('restaurant_settings_id', flat=True)
        .distinct()
    )
    if not rs_ids:
        return

    for rs_id in rs_ids:
        grid_map = {}
        for legacy_key, spec in LEGACY_GRIDS.items():
            obj, _ = SizeGrid.objects.get_or_create(
                key=spec['key'],
                restaurant_settings_id=rs_id,
                defaults={
                    'name': spec['name'],
                    'sizes': spec['sizes'],
                },
            )
            grid_map[legacy_key] = obj

        cats = Category.objects.filter(
            restaurant_settings_id=rs_id,
        ).exclude(size_grid_legacy='').exclude(size_grid_legacy__isnull=True)

        for cat in cats:
            grid_obj = grid_map.get(cat.size_grid_legacy)
            if grid_obj:
                cat.size_grid = grid_obj
                cat.save(update_fields=['size_grid'])


def unseed(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    Category.objects.update(size_grid=None)


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0026_size_grid_model_and_category_fk'),
    ]

    operations = [
        migrations.RunPython(seed_and_link, unseed),
    ]
