from django import forms

from product.models import TagType

from .models import ExpirationNoticeSetting


class TagTypeForm(forms.ModelForm):
    class Meta:
        model = TagType
        fields = ["tag_name"]
        labels = {"tag_name": "タグ名"}
        widgets = {
            "tag_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": 31,
                    "placeholder": "例：有機栽培",
                    "autocomplete": "off",
                }
            )
        }

    def clean_tag_name(self):
        raw_name = self.cleaned_data.get("tag_name", "")
        name = raw_name.strip()
        if not name:
            raise forms.ValidationError("タグ名を入力してください。")
        if len(name) > 31:
            raise forms.ValidationError("タグ名は31文字以内で入力してください。")
        existing = TagType.objects.filter(tag_name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("同じ名前のタグが既に存在します。")
        return name

class ExpirationNoticeSettingForm(forms.ModelForm):
    class Meta:
        model = ExpirationNoticeSetting
        fields = ['message', 'bg_color', 'text_color', 'is_active', 'notify_days_before']
        labels = {
            "message": "通知メッセージ",
            "bg_color": "背景色(下の四角を押して色を選択してください）",
            "text_color": "文字色(下の四角を押して色を選択してください）",
            "is_active": "通知を有効にする",
            'notify_days_before': "締め切り何日前に通知するか"
        }
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "例：この商品はもうすぐ締め切りです。"}),
            "bg_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "text_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }