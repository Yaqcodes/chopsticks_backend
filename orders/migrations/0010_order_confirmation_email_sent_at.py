from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_order_orders_orde_restaur_45a46a_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='confirmation_email_sent_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp when order confirmation email was sent (idempotent).',
                null=True,
            ),
        ),
    ]
