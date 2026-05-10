# Audit log for variant link/unlink

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
        ("menu", "0014_product_productimage_menuitem_product_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductVariantLinkEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("action", models.CharField(max_length=20)),
                ("product_id", models.BigIntegerField(blank=True, null=True)),
                ("menu_item_id", models.BigIntegerField()),
                ("previous_product_id", models.BigIntegerField(blank=True, null=True)),
                (
                    "acting_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant_settings",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variant_link_events",
                        to="core.restaurantsettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "Variant link event",
                "verbose_name_plural": "Variant link events",
                "ordering": ["-created_at"],
            },
        ),
    ]
