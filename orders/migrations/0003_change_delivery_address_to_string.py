# Generated manually to change delivery_address from ForeignKey to CharField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_payment_verified_at_order_paystack_access_code_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_address',
            field=models.CharField(blank=True, help_text='Delivery address as text (for guest orders)', max_length=500, null=True),
        ),
    ]
