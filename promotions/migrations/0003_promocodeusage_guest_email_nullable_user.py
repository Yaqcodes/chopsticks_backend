from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('promotions', '0002_add_restaurant_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocodeusage',
            name='guest_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='promocodeusage',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='promo_code_usages',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
