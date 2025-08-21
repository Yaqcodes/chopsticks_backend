# Generated manually for RestaurantSettings model enhancement

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantsettings',
            name='vat_rate',
            field=models.DecimalField(
                decimal_places=3,
                default=0.075,
                help_text='VAT rate as decimal (e.g., 0.075 for 7.5%)',
                max_digits=4
            ),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='pickup_delivery_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Fee for pickup orders',
                max_digits=8
            ),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='delivery_fee_base',
            field=models.DecimalField(
                decimal_places=2,
                default=500.00,
                help_text='Base delivery fee',
                max_digits=8
            ),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='delivery_fee_per_km',
            field=models.DecimalField(
                decimal_places=2,
                default=100.00,
                help_text='Additional fee per kilometer',
                max_digits=8
            ),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
