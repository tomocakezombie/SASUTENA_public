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
    family_name = forms.CharField(label="姓", max_length=128)
    given_name = forms.CharField(label="名", max_length=128)
    family_name_kana = forms.CharField(label="せい（ふりがな）", max_length=128)
    given_name_kana = forms.CharField(label="めい（ふりがな）", max_length=128)
    password = forms.CharField(widget=forms.PasswordInput, label="希望パスワード")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="確認用パスワード")

    class Meta:
        model = AccountRequest
        fields = ["username", "full_name", "full_name_kana", "email", "role", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role_field = self.fields.get("role")
        if role_field:
            role_field.choices = [choice for choice in role_field.choices if choice[0] in {"producer", "consumer"}]

        username_field = self.fields.get("username")
        if username_field:
            username_field.label = "ユーザーID"

        full_name_field = self.fields.get("full_name")
        if full_name_field:
            full_name_field.required = False
            full_name_field.widget = forms.HiddenInput()

        full_name_kana_field = self.fields.get("full_name_kana")
        if full_name_kana_field:
            full_name_kana_field.required = False
            full_name_kana_field.widget = forms.HiddenInput()

        for name in ["family_name", "given_name", "family_name_kana", "given_name_kana"]:
            field = self.fields.get(name)
            if field:
                field.widget.attrs.setdefault("class", "form-control")
                field.widget.attrs.setdefault("placeholder", field.label)

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
        family_name = self.cleaned_data.get("family_name", "").strip()
        given_name = self.cleaned_data.get("given_name", "").strip()
        separator = " " if family_name and given_name else ""
        instance.full_name = f"{family_name}{separator}{given_name}" or instance.full_name
        family_name_kana = self.cleaned_data.get("family_name_kana", "").strip()
        given_name_kana = self.cleaned_data.get("given_name_kana", "").strip()
        separator_kana = " " if family_name_kana and given_name_kana else ""
        instance.full_name_kana = (
            f"{family_name_kana}{separator_kana}{given_name_kana}" or instance.full_name_kana
        )
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