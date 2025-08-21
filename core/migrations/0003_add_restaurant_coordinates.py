# Generated manually to add restaurant coordinates for distance calculations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_restaurant_settings_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantsettings',
            name='restaurant_latitude',
            field=models.DecimalField(decimal_places=6, default=9.0820, help_text='Restaurant latitude coordinate', max_digits=9),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='restaurant_longitude',
            field=models.DecimalField(decimal_places=6, default=7.3986, help_text='Restaurant longitude coordinate', max_digits=9),
        ),
    ]
