from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0019_rename_menu_menuite_product_7e4f1e_idx_menu_menuit_product_242f34_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='gender',
            field=models.CharField(
                blank=True,
                choices=[('men', 'Men'), ('women', 'Women')],
                help_text='Which Men/Women nav tab lists this category (Zmall storefront).',
                max_length=20,
                null=True,
            ),
        ),
    ]
