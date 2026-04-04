# Generated manually for plan: on_sale + sale_price

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("menu", "0012_alter_menuitem_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="menuitem",
            name="on_sale",
            field=models.BooleanField(
                default=False,
                help_text="When True, customers pay sale_price (must be set). Source of truth for sale state.",
            ),
        ),
        migrations.AddField(
            model_name="menuitem",
            name="sale_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Discounted price when on_sale is True.",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
