# OAuth fields on RestaurantSettings (business-specific Google OAuth)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_quote"),
    ]

    operations = [
        migrations.AddField(
            model_name="restaurantsettings",
            name="google_oauth_client_id",
            field=models.CharField(
                blank=True,
                help_text="Google OAuth 2.0 Client ID for this business",
                max_length=255,
                default="",
            ),
        ),
        migrations.AddField(
            model_name="restaurantsettings",
            name="google_oauth_client_secret",
            field=models.CharField(
                blank=True,
                help_text="Google OAuth 2.0 Client Secret for this business",
                max_length=255,
                default="",
            ),
        ),
    ]
