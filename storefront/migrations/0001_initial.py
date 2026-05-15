import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0014_restaurantsettings_catalog_listing_mode'),
        ('menu', '0018_backfill_menuitem_size_from_sizes'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpotlightPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='spotlights/')),
                ('external_url', models.URLField(blank=True, help_text='Optional link (Instagram post, article, etc.).')),
                ('caption', models.CharField(blank=True, max_length=255)),
                ('cta_label', models.CharField(blank=True, default='Shop the look', help_text='Short label shown on hover in the carousel.', max_length=64)),
                ('placement', models.SlugField(choices=[('shop_the_look', 'Shop the look (social carousel)'), ('homepage_carousel', 'Homepage carousel')], db_index=True, default='shop_the_look', max_length=64)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('restaurant_settings', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spotlight_posts', to='core.restaurantsettings')),
            ],
            options={
                'verbose_name': 'Spotlight post',
                'verbose_name_plural': 'Spotlight posts',
                'ordering': ['sort_order', '-created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='SpotlightPostLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('menu_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='spotlight_links', to='menu.menuitem')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='spotlight_links', to='menu.product')),
                ('spotlight', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='storefront.spotlightpost')),
            ],
            options={
                'verbose_name': 'Spotlight link',
                'verbose_name_plural': 'Spotlight links',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='spotlightpost',
            index=models.Index(fields=['restaurant_settings', 'placement', 'is_active', 'sort_order'], name='storefront__restaur_8e0f0d_idx'),
        ),
    ]
