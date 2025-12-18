from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_userevaluation"),
    ]

    operations = [
        migrations.AddField(
            model_name="userevaluation",
            name="comment",
            field=models.TextField(blank=True, null=True, verbose_name="コメント"),
        ),
    ]
