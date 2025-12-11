from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import secrets


ROLE_CHOICES = [
    ("proceduct", "生産者"),
    ("consumer", "消費者"),
]

# カスタムユーザーモデル ロール追加
class CustomUser(AbstractUser):
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="user")
    redirect_authenticated_user = True

# 新規アカウント作成時のリクエスト
class AccountRequest(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="user")
    password = models.CharField(max_length=128)
    request_date = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_expires_at = models.DateTimeField(blank=True, null=True)

    def generate_verification_code(self):
        code = f"{secrets.randbelow(1000000):06d}"
        self.verification_code = code
        self.verification_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=["verification_code", "verification_expires_at"])
        return code

    def __str__(self):
        return self.username