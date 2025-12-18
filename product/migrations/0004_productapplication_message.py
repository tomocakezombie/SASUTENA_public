from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0003_rename_id_to_apply_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="productapplication",
            name="message",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="productapplication",
            name="quantity",
            field=models.DecimalField(decimal_places=0, default=1, max_digits=31),
        ),
    ]
