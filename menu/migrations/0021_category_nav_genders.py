from django.db import migrations, models


def _infer_nav_genders(category, Product):
    nav = set()
    legacy = getattr(category, 'gender', None)
    if legacy in ('men', 'women', 'unisex'):
        nav.add(legacy)
    product_genders = set(
        Product.objects.filter(category_id=category.pk, is_available=True)
        .exclude(gender__isnull=True)
        .exclude(gender='')
        .values_list('gender', flat=True)
        .distinct()
    )
    for pg in product_genders:
        if pg in ('men', 'women', 'unisex'):
            nav.add(pg)
    if not nav:
        nav = {'men', 'women'}
    return sorted(nav)


def forwards_nav_genders(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    Product = apps.get_model('menu', 'Product')
    for cat in Category.objects.all().iterator():
        if (cat.name or '').strip().lower() == 'none':
            cat.nav_genders = []
            cat.save(update_fields=['nav_genders'])
            continue
        nav = _infer_nav_genders(cat, Product)
        cat.nav_genders = nav
        cat.save(update_fields=['nav_genders'])


def backwards_nav_genders(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all().iterator():
        nav = cat.nav_genders if isinstance(cat.nav_genders, list) else []
        if 'men' in nav and 'women' not in nav and 'unisex' not in nav:
            cat.gender = 'men'
        elif 'women' in nav and 'men' not in nav and 'unisex' not in nav:
            cat.gender = 'women'
        else:
            cat.gender = None
        cat.save(update_fields=['gender'])


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0020_category_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='nav_genders',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Storefront nav audiences: men, women, and/or unisex (unisex shows in both tabs).',
            ),
        ),
        migrations.RunPython(forwards_nav_genders, backwards_nav_genders),
        migrations.RemoveField(
            model_name='category',
            name='gender',
        ),
    ]
