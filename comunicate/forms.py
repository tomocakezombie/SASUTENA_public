from django import forms
from django.contrib.auth import get_user_model

from .models import Message
from product.models import Product


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["message_content", "item"]
        widgets = {
            "message_content": forms.Textarea(
                attrs={"rows": 2, "placeholder": "メッセージを入力...", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].widget.attrs.setdefault("class", "form-select")

    def clean_message_content(self):
        content = self.cleaned_data["message_content"].strip()
        if not content:
            raise forms.ValidationError("メッセージを入力してください。")
        return content


class MessageEditForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["message_content"]
        widgets = {
            "message_content": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_message_content(self):
        content = self.cleaned_data["message_content"].strip()
        if not content:
            raise forms.ValidationError("メッセージを入力してください。")
        return content


class ConversationStartForm(forms.Form):
    receiver = forms.ModelChoiceField(queryset=get_user_model().objects.none(), label="ユーザー")
    item = forms.ModelChoiceField(
        queryset=Product.objects.none(), required=False, label="商品", empty_label="(指定なし)"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        qs = user_model.objects.exclude(pk=user.pk) if user else user_model.objects.all()
        self.fields["receiver"].queryset = qs.order_by("username")
        product_qs = Product.objects.all().order_by("item_name")
        self.fields["item"].queryset = product_qs
        self.fields["receiver"].widget.attrs.update({"class": "form-select"})
        self.fields["item"].widget.attrs.update({"class": "form-select"})

        def label_user(u):
            if hasattr(u, "get_role_display"):
                return f"{u.username} ({u.get_role_display()})"
            return u.username

        self.fields["receiver"].label_from_instance = label_user
