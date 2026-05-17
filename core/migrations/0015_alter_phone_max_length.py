from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_restaurantsettings_catalog_listing_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='restaurantsettings',
            name='phone',
            field=models.CharField(default='+234', max_length=80),
        ),
        migrations.AlterField(
            model_name='quote',
            name='phone',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
