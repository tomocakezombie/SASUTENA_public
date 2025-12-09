from django.db import models
from django.conf import settings # login がCustomUserを参照

class UserProfile(models.Model):
    #
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, # 'login.CustomUser' 
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # ユーザーDB
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="名前")
    nick_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="ニックネーム")
    icon_image = models.ImageField(upload_to='icons/', blank=True, null=True, verbose_name="アイコン画像")
    content_profile = models.TextField(max_length=511, blank=True, null=True, verbose_name="プロフィール内容")
    publish_profile = models.BooleanField(default=True, verbose_name="プロフィール公開")
    memo = models.TextField(max_length=511, blank=True, null=True, verbose_name="利用者メモ")
    mail_allow = models.BooleanField(default=True, verbose_name="メール通知")

    def __str__(self):
        return f"{self.user.username} - Profile"
