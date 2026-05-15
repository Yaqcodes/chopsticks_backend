from django.db import migrations, models


def set_zmall_catalog_listing_mode(apps, schema_editor):
    RestaurantSettings = apps.get_model('core', 'RestaurantSettings')
    for rs in RestaurantSettings.objects.filter(domain__icontains='zmall'):
        rs.catalog_listing_mode = 'product'
        rs.save(update_fields=['catalog_listing_mode'])
    Product = apps.get_model('menu', 'Product')
    tenant_ids = set(Product.objects.values_list('restaurant_settings_id', flat=True))
    for rs in RestaurantSettings.objects.filter(pk__in=tenant_ids).exclude(catalog_listing_mode='product'):
        rs.catalog_listing_mode = 'product'
        rs.save(update_fields=['catalog_listing_mode'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_alter_restaurantsettings_google_oauth_client_id_and_more'),
        ('menu', '0018_backfill_menuitem_size_from_sizes'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantsettings',
            name='catalog_listing_mode',
            field=models.CharField(
                choices=[('menu_item', 'Menu items (SKUs)'), ('product', 'Grouped catalog products')],
                default='menu_item',
                help_text='Whether public catalog UIs and spotlight links use grouped Products or MenuItems.',
                max_length=20,
            ),
        ),
        migrations.RunPython(set_zmall_catalog_listing_mode, migrations.RunPython.noop),
    ]
