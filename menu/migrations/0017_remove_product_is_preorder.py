from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0016_product_is_preorder"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="is_preorder",
        ),
    ]
