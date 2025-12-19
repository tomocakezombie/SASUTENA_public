from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0005_update_role_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="password_reset_tokens",
                        to="login.customuser",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
