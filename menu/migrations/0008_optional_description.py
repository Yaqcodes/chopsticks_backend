# Generated for optional product description

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("menu", "0007_alter_menuitem_images"),
    ]

    operations = [
        migrations.AlterField(
            model_name="menuitem",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
