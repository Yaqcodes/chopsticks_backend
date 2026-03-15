# Generated manually for payment-success SKU decrement

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0007_rename_orders_order_rest_sett_order_num_idx_orders_orde_restaur_85f0d7_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stock_reduced",
            field=models.BooleanField(
                default=False,
                help_text="True after payment success reduced menu item SKU; restored on refund/cancel.",
            ),
        ),
    ]
