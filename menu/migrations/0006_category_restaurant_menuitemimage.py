# Category business-specific; MenuItemImage for multiple uploads

from django.db import migrations, models
import django.db.models.deletion


def assign_category_tenants(apps, schema_editor):
    """Assign existing categories to tenants by slug or menu items."""
    Category = apps.get_model('menu', 'Category')
    RestaurantSettings = apps.get_model('core', 'RestaurantSettings')
    MenuItem = apps.get_model('menu', 'MenuItem')

    roschi = RestaurantSettings.objects.filter(domain__icontains='roschi').first()
    zmall = RestaurantSettings.objects.filter(domain__icontains='zmall').first()
    chopsticks = RestaurantSettings.objects.filter(domain__icontains='chopsticks').first()
    default = roschi or zmall or chopsticks or RestaurantSettings.objects.first()

    roschi_slugs = {'bottled-water', 'sachet-water'}
    zmall_slugs = {'pants', 'shoes', 'bags', 'accessories', 'dresses', 'shirts'}

    for cat in Category.objects.all():
        if cat.restaurant_settings_id:
            continue
        slug = (cat.slug or '').lower()
        if slug in roschi_slugs and roschi:
            cat.restaurant_settings = roschi
        elif slug in zmall_slugs and zmall:
            cat.restaurant_settings = zmall
        else:
            # Assign to tenant that has menu items in this category
            mi = MenuItem.objects.filter(category=cat).select_related('restaurant_settings').first()
            if mi and mi.restaurant_settings_id:
                cat.restaurant_settings = mi.restaurant_settings
            elif default:
                cat.restaurant_settings = default
        if cat.restaurant_settings_id:
            cat.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_add_restaurantsettings_paystack_and_domain'),
        ('menu', '0005_alter_menuitem_gender'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='restaurant_settings',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='categories',
                to='core.restaurantsettings',
            ),
        ),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, max_length=100, null=True, unique=False),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('restaurant_settings', 'slug')},
        ),
        migrations.CreateModel(
            name='MenuItemImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='menu_items/extra/')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('menu_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='extra_images',
                    to='menu.menuitem',
                )),
            ],
            options={'ordering': ['sort_order', 'id']},
        ),
        migrations.RunPython(assign_category_tenants, migrations.RunPython.noop),
    ]
