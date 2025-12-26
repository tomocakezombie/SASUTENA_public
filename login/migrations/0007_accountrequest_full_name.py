from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0006_passwordresettoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountrequest",
            name="full_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="氏名"),
        ),
    ]
