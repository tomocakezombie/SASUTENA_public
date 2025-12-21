from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0006_alter_productcomment_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="rejected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
