from django.db import migrations


def forwards(apps, schema_editor):
    """
    Copy the sole value from ``MenuItem.sizes`` (JSON list) into ``MenuItem.size``.

    Only when ``sizes`` has exactly one non-empty entry (after strip). If ``size`` is
    already non-empty, it is left unchanged. Rows with zero or multiple non-empty
    ``sizes`` entries are skipped.
    """
    MenuItem = apps.get_model("menu", "MenuItem")
    max_len = MenuItem._meta.get_field("size").max_length
    batch = []
    for item in MenuItem.objects.all().only("id", "size", "sizes").iterator(chunk_size=500):
        if (item.size or "").strip():
            continue
        sizes = item.sizes
        if not isinstance(sizes, list):
            continue
        vals = [str(s).strip() for s in sizes if s is not None and str(s).strip()]
        if len(vals) != 1:
            continue
        item.size = vals[0][:max_len]
        batch.append(item)
        if len(batch) >= 500:
            MenuItem.objects.bulk_update(batch, ["size"])
            batch.clear()
    if batch:
        MenuItem.objects.bulk_update(batch, ["size"])


def backwards(apps, schema_editor):
    # Cannot know which ``size`` values came from this migration vs manual entry.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0017_remove_product_is_preorder"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
