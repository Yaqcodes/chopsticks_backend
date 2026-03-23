# Make product (MenuItem) primary image mandatory

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0009_backfill_menuitem_image_from_extra'),
    ]

    operations = [
        migrations.AlterField(
            model_name='menuitem',
            name='image',
            field=models.ImageField(blank=False, null=True, upload_to='menu_items/'),
        ),
    ]
