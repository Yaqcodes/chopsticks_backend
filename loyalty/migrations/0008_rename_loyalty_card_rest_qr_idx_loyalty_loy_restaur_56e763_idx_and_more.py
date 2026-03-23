# Rename indexes on LoyaltyCard (DB already has short names; state unchanged)

from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0007_make_loyalty_business_scoped"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(noop, noop)],
            state_operations=[],
        ),
    ]
