# Rename index on Order (DB already has short name; state unchanged)

from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_make_order_number_tenant_scoped"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(noop, noop)],
            state_operations=[],
        ),
    ]
