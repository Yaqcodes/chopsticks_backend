from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0015_productvariantlinkevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_preorder",
            field=models.BooleanField(
                default=False,
                help_text="When enabled, storefront shows a Pre-Order badge and the cart button reads Pre-Order (same add-to-cart flow).",
            ),
        ),
    ]
