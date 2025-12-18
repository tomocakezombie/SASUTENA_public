from django.db import migrations, models


def _normalize_roles(apps, schema_editor):
    User = apps.get_model("login", "CustomUser")
    AccountRequest = apps.get_model("login", "AccountRequest")

    for user in User.objects.all():
        original = user.role or ""
        normalized = original
        if original == "proceduct":
            normalized = "producer"
        elif original == "user":
            normalized = "admin" if (user.is_staff or user.is_superuser) else "consumer"
        if normalized != original:
            user.role = normalized
            user.save(update_fields=["role"])

    for request in AccountRequest.objects.all():
        original = request.role or ""
        normalized = original
        if original == "proceduct":
            normalized = "producer"
        elif original == "user":
            normalized = "consumer"
        if normalized != original:
            request.role = normalized
            request.save(update_fields=["role"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0004_alter_accountrequest_role_alter_customuser_role"),
    ]

    operations = [
        migrations.RunPython(_normalize_roles, _noop),
        migrations.AlterField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[("producer", "生産者"), ("consumer", "消費者"), ("admin", "管理者")],
                default="consumer",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="accountrequest",
            name="role",
            field=models.CharField(
                choices=[("producer", "生産者"), ("consumer", "消費者"), ("admin", "管理者")],
                default="consumer",
                max_length=50,
            ),
        ),
    ]
