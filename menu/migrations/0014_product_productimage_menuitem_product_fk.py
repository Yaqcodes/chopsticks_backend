# Product grouped catalog + nullable MenuItem.product FK

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("menu", "0013_menuitem_on_sale_sale_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(blank=True, max_length=160)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "gender",
                    models.CharField(
                        blank=True,
                        choices=[("men", "Male"), ("women", "Female"), ("unisex", "Unisex")],
                        help_text="Shown on storefront; distinct from MenuItem apparel fields.",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "base_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Informational listing price only; variants charge MenuItem.price.",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ("badges", models.JSONField(blank=True, default=list)),
                ("is_available", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("meta_title", models.CharField(blank=True, max_length=200)),
                ("meta_description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="catalog_products",
                        to="menu.category",
                    ),
                ),
                (
                    "restaurant_settings",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="catalog_products",
                        to="core.restaurantsettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "ZMall Catalog Product",
                "verbose_name_plural": "ZMall Catalog Products",
                "ordering": ["sort_order", "-created_at", "name"],
            },
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="products/")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery_images",
                        to="menu.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Product Image",
                "verbose_name_plural": "Product Images",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["restaurant_settings", "is_available"], name="menu_produc_restaur_5c8b2d_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together={("restaurant_settings", "slug")},
        ),
        migrations.AddField(
            model_name="menuitem",
            name="product",
            field=models.ForeignKey(
                blank=True,
                help_text="ZMall grouped product parent; manual link only. Leave blank for non-grouped SKUs.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="variants",
                to="menu.product",
            ),
        ),
        migrations.AddIndex(
            model_name="menuitem",
            index=models.Index(fields=["product"], name="menu_menuite_product_7e4f1e_idx"),
        ),
    ]
