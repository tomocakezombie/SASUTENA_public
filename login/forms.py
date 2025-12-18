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