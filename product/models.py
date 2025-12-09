from django.db import models
from django.contrib.auth.models import UserAttributeSimilarityValidator

class Product(models.Model):
    itrm_id = models.AutoField(primary_key = True)
    item_name = models.CharField(max_length = 511)
    number = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.CharField(max_length = 511)
    item_image = models.ImageField(upload_to = 'product/', null = True, blank = True)
    publish = models.BooleanField(default = False)
    valid = models.BooleanField(default = False)
    completed = models.BooleanField(default = False)
    user_id = ForeignKey(User, on_delete = models.CASCADE)
    admin_comment = models.CharField(max_length = 511, null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)   #登録日時（自動）
    
    def __str__(self):
        return f"{self.item_name} (ID: {self.item_id})"
    
