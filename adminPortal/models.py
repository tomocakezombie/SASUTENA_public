from django.db import models


class ExpirationNoticeSetting(models.Model):
    message = models.TextField(
        default="{{user}}さんが出品した{{item}}の受け渡し期間が間もなく終了します！"
                "受け渡しが完了したら，あなたは食品ロス削減に貢献出来ます！"
    )
    bg_color = models.CharField(max_length=20, default="#ffc107")  
    text_color = models.CharField(max_length=20, default="#000000")
    is_active = models.BooleanField(default=True)
    notify_days_before = models.PositiveIntegerField(default=3, help_text="締め切り何日前に通知するか")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"通知設定 {self.pk} ({'有効' if self.is_active else '無効'})"


class ProductApprovalSetting(models.Model):
    auto_publish_new_products = models.BooleanField(
        default=False,
        verbose_name="新規出品を自動公開する",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "出品承認設定"
        verbose_name_plural = "出品承認設定"

    def __str__(self):
        state = "自動公開" if self.auto_publish_new_products else "手動承認"
        return f"出品承認設定 ({state})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def is_auto_publish_enabled(cls):
        return cls.get_solo().auto_publish_new_products