# Add restaurant_settings to PromoCode (business-scoped)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_add_restaurantsettings_paystack_and_domain"),
        ("promotions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="promocode",
            name="restaurant_settings",
            field=models.ForeignKey(
                blank=True,
                help_text="Business this promo code belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promo_codes",
                to="core.restaurantsettings",
            ),
        ),
        migrations.AlterField(
            model_name="promocode",
            name="code",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterUniqueTogether(
            name="promocode",
            unique_together={("restaurant_settings", "code")},
        ),
    ]
