# login/forms.py
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import CustomUser, AccountRequest

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "role")

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ("username", "email", "role")

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="希望パスワード")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="確認用パスワード")

    class Meta:
        model = AccountRequest
        fields = ["username", "email", "role", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role_field = self.fields.get("role")
        if role_field:
            role_field.choices = [choice for choice in role_field.choices if choice[0] in {"producer", "consumer"}]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "パスワードが一致しません。")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class VerificationForm(forms.Form):
    email = forms.EmailField(label="メールアドレス")
    code = forms.CharField(label="認証コード", max_length=6)


class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(
        label="ログインID（ユーザー名）",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "username",
                "placeholder": "例: producer1",
                "required": "required",
            }
        ),
    )
    email = forms.EmailField(
        label="連絡先メールアドレス",
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
            }
        ),
    )
    note = forms.CharField(
        label="補足（任意）",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "ログインできなくなった経緯など",
            }
        ),
    )

    user = None

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        email = cleaned.get("email")

        if not username:
            return cleaned

        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            self.add_error("username", "該当するユーザーが見つかりません。")
            return cleaned

        if email and user.email:
            if email.strip().lower() != user.email.lower():
                self.add_error("email", "登録済みのメールアドレスと一致していません。")

        self.user = user
        return cleaned