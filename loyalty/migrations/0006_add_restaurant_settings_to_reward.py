# Add restaurant_settings to Reward (business-scoped)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_add_restaurantsettings_paystack_and_domain"),
        ("loyalty", "0005_add_default_expiration_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="reward",
            name="restaurant_settings",
            field=models.ForeignKey(
                blank=True,
                help_text="Business this reward belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rewards",
                to="core.restaurantsettings",
            ),
        ),
    ]
