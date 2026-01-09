from django.db import migrations, models


def bootstrap_setting(apps, schema_editor):
    setting_model = apps.get_model("adminPortal", "ProductApprovalSetting")
    setting_model.objects.get_or_create(pk=1)


def teardown_setting(apps, schema_editor):
    setting_model = apps.get_model("adminPortal", "ProductApprovalSetting")
    setting_model.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("adminPortal", "0003_remove_expirationnoticesetting_notify_hour"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductApprovalSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auto_publish_new_products", models.BooleanField(default=False, verbose_name="新規出品を自動公開する")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "出品承認設定",
                "verbose_name_plural": "出品承認設定",
            },
        ),
        migrations.RunPython(bootstrap_setting, teardown_setting),
    ]
