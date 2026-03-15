# Data migration: fill empty MenuItem.image from first additional image (MenuItemImage)

from django.db import migrations, models


def backfill_menuitem_image(apps, schema_editor):
    """For each MenuItem with no primary image, set image from first extra image."""
    MenuItem = apps.get_model('menu', 'MenuItem')
    MenuItemImage = apps.get_model('menu', 'MenuItemImage')
    updated = 0
    for item in MenuItem.objects.filter(models.Q(image='') | models.Q(image__isnull=True)):
        first_extra = (
            MenuItemImage.objects.filter(menu_item=item)
            .order_by('sort_order', 'id')
            .first()
        )
        if first_extra and first_extra.image:
            item.image = first_extra.image
            item.save(update_fields=['image'])
            updated += 1
    if updated:
        print(f"Backfilled primary image for {updated} menu item(s) from additional images.")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0008_optional_description'),
    ]

    operations = [
        migrations.RunPython(backfill_menuitem_image, noop),
    ]
