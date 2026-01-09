from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import secrets


ROLE_CHOICES = [
    ("producer", "生産者"),
    ("consumer", "消費者"),
    ("admin", "管理者"),
]

# カスタムユーザーモデル ロール追加
class CustomUser(AbstractUser):
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="consumer")
    redirect_authenticated_user = True

# 新規アカウント作成時のリクエスト
class AccountRequest(models.Model):
    username = models.CharField(max_length=150)
    full_name = models.CharField(max_length=255, blank=True, verbose_name="氏名")
    email = models.EmailField()
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="consumer")
    password = models.CharField(max_length=128)
    request_date = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False, verbose_name="メール認証済み")
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    full_name_kana = models.CharField(max_length=255, blank=True, verbose_name="氏名（かな）")
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


class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_used(self):
        if not self.used_at:
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_valid(self):
        return not self.used_at and not self.is_expired