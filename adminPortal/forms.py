from django import forms

from product.models import TagType


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
