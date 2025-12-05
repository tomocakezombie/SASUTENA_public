from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, AccountRequest
from .forms import CustomUserCreationForm, CustomUserChangeForm

# /admin/ の管理者ページから自作ユーザーを管理できるように設定してます
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("role",)}),)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "role"),
        }),
    )

admin.site.register(AccountRequest)