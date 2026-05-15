from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0022_category_nav_booleans'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='display_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional label for nav and category pages. Leave blank to use Name.',
                max_length=100,
            ),
        ),
    ]
