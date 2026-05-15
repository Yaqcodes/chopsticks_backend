from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storefront', '0002_rename_storefront__restaur_8e0f0d_idx_storefront__restaur_0a47eb_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spotlightpost',
            name='image',
            field=models.ImageField(upload_to='storefront/'),
        ),
    ]
