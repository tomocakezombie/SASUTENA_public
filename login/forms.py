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
        fields = ["username", "full_name", "email", "role", "password"]
        labels = {
            "full_name": "氏名",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role_field = self.fields.get("role")
        if role_field:
            role_field.choices = [choice for choice in role_field.choices if choice[0] in {"producer", "consumer"}]

        full_name_field = self.fields.get("full_name")
        if full_name_field:
            full_name_field.required = True

        for name, field in self.fields.items():
            widget = field.widget
            base_class = "form-select" if isinstance(widget, forms.Select) else "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = (f"{existing} {base_class}").strip()
            if not widget.attrs.get("placeholder") and isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput)):
                widget.attrs["placeholder"] = field.label

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
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "required": "required",
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

        if not user.email:
            self.add_error("username", "このユーザーにはメールアドレスが登録されていません。管理者へお問い合わせください。")
            return cleaned

        if email.strip().lower() != user.email.lower():
            self.add_error("email", "登録済みのメールアドレスと一致していません。")
            return cleaned

        self.user = user
        return cleaned


class PasswordResetConfirmForm(forms.Form):
    new_password1 = forms.CharField(
        label="新しいパスワード",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "新しいパスワード",
            }
        ),
        min_length=8,
    )
    new_password2 = forms.CharField(
        label="新しいパスワード（確認）",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "新しいパスワードを再入力",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "パスワードが一致しません。")
        return cleaned