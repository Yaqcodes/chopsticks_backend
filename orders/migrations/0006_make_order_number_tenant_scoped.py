# Make order_number unique per tenant (restaurant_settings, order_number)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_alter_order_options_alter_orderitem_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="order_number",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterUniqueTogether(
            name="order",
            unique_together={("restaurant_settings", "order_number")},
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["restaurant_settings", "order_number"],
                name="orders_orde_restaur_85f0d7_idx",
            ),
        ),
    ]
