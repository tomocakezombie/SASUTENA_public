from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # 一覧に表示するフィールド
    list_display = ('user', 'nick_name', 'role_display', 'publish_profile')
    
    # ユーザー名やニックネームで検索できるようにする
    search_fields = ('user__username', 'nick_name', 'name')

    # ヘルパーメソッド：関連するUserモデルのロールを表示
    def role_display(self, obj):
        return obj.user.role
    role_display.short_description = "ロール"