from django.db import migrations, models


def forwards_from_nav_genders(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all().iterator():
        nav = cat.nav_genders if isinstance(cat.nav_genders, list) else []
        cat.show_in_men = 'men' in nav
        cat.show_in_women = 'women' in nav
        cat.show_in_unisex = 'unisex' in nav
        cat.save(update_fields=['show_in_men', 'show_in_women', 'show_in_unisex'])


def backwards_to_nav_genders(apps, schema_editor):
    Category = apps.get_model('menu', 'Category')
    for cat in Category.objects.all().iterator():
        nav = []
        if cat.show_in_men:
            nav.append('men')
        if cat.show_in_women:
            nav.append('women')
        if cat.show_in_unisex:
            nav.append('unisex')
        cat.nav_genders = nav
        cat.save(update_fields=['nav_genders'])


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0021_category_nav_genders'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='show_in_men',
            field=models.BooleanField(default=False, help_text='List this category under the Men nav tab.'),
        ),
        migrations.AddField(
            model_name='category',
            name='show_in_women',
            field=models.BooleanField(default=False, help_text='List this category under the Women nav tab.'),
        ),
        migrations.AddField(
            model_name='category',
            name='show_in_unisex',
            field=models.BooleanField(default=False, help_text='List in both Men and Women nav (shared / unisex shelf).'),
        ),
        migrations.RunPython(forwards_from_nav_genders, backwards_to_nav_genders),
        migrations.RemoveField(
            model_name='category',
            name='nav_genders',
        ),
    ]
