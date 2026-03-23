# Make LoyaltyCard business-scoped (restaurant_settings required, unique_together, indexes)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_add_restaurantsettings_paystack_and_domain"),
        ("loyalty", "0006_add_restaurant_settings_to_reward"),
    ]

    operations = [
        migrations.AddField(
            model_name="loyaltycard",
            name="restaurant_settings",
            field=models.ForeignKey(
                default=1,
                help_text="Business this loyalty card belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="loyalty_cards",
                to="core.restaurantsettings",
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name="loyaltycard",
            unique_together={("restaurant_settings", "qr_code")},
        ),
        migrations.AddIndex(
            model_name="loyaltycard",
            index=models.Index(
                fields=["restaurant_settings", "qr_code"],
                name="loyalty_loy_restaur_56e763_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="loyaltycard",
            index=models.Index(
                fields=["user", "restaurant_settings"],
                name="loyalty_loy_user_id_13ac4d_idx",
            ),
        ),
    ]
