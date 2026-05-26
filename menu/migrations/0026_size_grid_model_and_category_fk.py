"""
Step 1: Create SizeGrid model and add the new FK on Category.
The old CharField (size_grid) is renamed to size_grid_legacy so both coexist.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_restaurantsettings_opening_hours_blank"),
        ("menu", "0025_category_size_grid_women_shoes"),
    ]

    operations = [
        migrations.CreateModel(
            name="SizeGrid",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text='Descriptive label, e.g. "Men\'s Shoes EU 40\u201347".',
                        max_length=100,
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        help_text="URL-safe identifier sent to the storefront API (auto-generated from name).",
                    ),
                ),
                (
                    "sizes",
                    models.JSONField(
                        default=list,
                        help_text='Ordered list of sizes, e.g. ["S","M","L","XL"] or ["40","41","42"].',
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "restaurant_settings",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="size_grids",
                        to="core.restaurantsettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "Size Grid",
                "verbose_name_plural": "Size Grids",
                "ordering": ["name"],
                "unique_together": {("key", "restaurant_settings")},
            },
        ),
        migrations.RenameField(
            model_name="category",
            old_name="size_grid",
            new_name="size_grid_legacy",
        ),
        migrations.AddField(
            model_name="category",
            name="size_grid",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="categories",
                to="menu.sizegrid",
                help_text="Pick a size grid, or leave blank for flexible sizing (perfume, bags, etc.).",
            ),
        ),
    ]
