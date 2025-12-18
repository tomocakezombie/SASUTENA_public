# Generated manually for ProductApplication model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductApplication",
            fields=[
                (
                    "apply_id",
                    models.BigAutoField(primary_key=True, serialize=False),
                ),
                (
                    "hope_time",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "apply_time",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=0, max_digits=31),
                ),
                (
                    "apply_status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "申請中"),
                            (1, "承認"),
                            (2, "拒否"),
                            (3, "キャンセル"),
                        ],
                        default=0,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applications",
                        to="product.product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "申込み",
                "verbose_name_plural": "申込み",
                "ordering": ("-apply_time",),
            },
        ),
    ]
