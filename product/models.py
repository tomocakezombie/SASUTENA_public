from django.db import models
from django.conf import settings
from django.utils import timezone


class Product(models.Model):
    item_id = models.AutoField(primary_key=True)
    item_name = models.CharField(max_length=511)
    number = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.CharField(max_length=511)
    item_image = models.ImageField(upload_to='product/', null=True, blank=True)
    publish = models.BooleanField(default=False)
    valid = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    admin_comment = models.CharField(max_length=511, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.item_name} (ID: {self.item_id})"


class ProductApplication(models.Model):
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_DECLINED = 2
    STATUS_CANCELLED = 3

    STATUS_CHOICES = (
        (STATUS_PENDING, "申請中"),
        (STATUS_APPROVED, "承認"),
        (STATUS_DECLINED, "拒否"),
        (STATUS_CANCELLED, "キャンセル"),
    )

    apply_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_applications",
    )
    hope_time = models.DateTimeField(null=True, blank=True)
    apply_time = models.DateTimeField(auto_now_add=True)
    quantity = models.DecimalField(max_digits=31, decimal_places=0, default=1)
    message = models.TextField(blank=True)
    apply_status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    class Meta:
        verbose_name = "申込み"
        verbose_name_plural = "申込み"
        ordering = ("-apply_time",)

    def __str__(self):
        return f"Application {self.apply_id} for {self.product} by {self.user}"


class ProductComment(models.Model):
    item_comment_id = models.BigAutoField(primary_key=True, db_column="item_comment_id")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_comments",
    )
    content = models.CharField(max_length=511, db_column="content")
    comment_time = models.DateTimeField(auto_now_add=True, db_column="comment_time")
    delete_flag = models.BooleanField(default=False, db_column="delete_flag")
    edit_flag = models.BooleanField(default=False, db_column="edit_flag")

    class Meta:
        ordering = ("-comment_time",)
        db_table = "product_productcomment"

    def __str__(self):
        return f"Comment by {self.user} on {self.product}"


class ProductCommentMention(models.Model):
    comment = models.ForeignKey(
        ProductComment,
        on_delete=models.CASCADE,
        related_name="mentions",
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentioned_in_product_comments",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "product_productcommentmention"
        unique_together = ("comment", "mentioned_user")

    def __str__(self):
        return f"{self.comment_id} -> {self.mentioned_user}"