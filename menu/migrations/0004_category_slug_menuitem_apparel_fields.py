# Generated for MenuItem expansion (apparel) and Category slug

from django.db import migrations, models


def populate_category_slugs(apps, schema_editor):
    """Generate slugs from existing category names."""
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all():
        if not cat.slug:
            cat.slug = slugify(cat.name) if hasattr(cat, 'name') else f'category-{cat.id}'
            # Ensure uniqueness
            base = cat.slug
            n = 0
            while Category.objects.filter(slug=cat.slug).exclude(pk=cat.pk).exists():
                n += 1
                cat.slug = f'{base}-{n}'
            cat.save()


def slugify(name):
    """Simple slugify: lowercase, replace spaces with hyphens, alphanumeric + hyphens."""
    s = name.lower().strip()
    s = ''.join(c if c.isalnum() or c in ' -' else '' for c in s)
    return '-'.join(s.split())[:100]


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0003_alter_category_options_alter_menuitem_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, null=True, max_length=100, unique=True),
        ),
        migrations.AddField(
            model_name='menuitem',
            name='gender',
            field=models.CharField(
                blank=True,
                choices=[('men', 'Male'), ('women', 'Female'), ('unisex', 'Unisex')],
                help_text='Target gender (apparel). Leave blank for food/beverage.',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='menuitem',
            name='sizes',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Size options as list (e.g. ["S", "M", "L"]). For apparel.',
            ),
        ),
        migrations.AddField(
            model_name='menuitem',
            name='colors',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Color options as list of {"name": "...", "hex": "#..."}. For apparel.',
            ),
        ),
        migrations.AddField(
            model_name='menuitem',
            name='images',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Additional image URLs or paths. Primary image uses image field.',
            ),
        ),
        migrations.RunPython(populate_category_slugs, migrations.RunPython.noop),
    ]
