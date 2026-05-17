from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_alter_phone_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='restaurantsettings',
            name='opening_hours',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Optional JSON per weekday (monday–sunday). Each value is "HH:MM" or null if closed. '
                    'Example: {"monday": "09:00", "sunday": null}. Leave empty to use opening/closing time only.'
                ),
            ),
        ),
    ]
