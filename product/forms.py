from django import forms
from .models import Product, ProductApplication

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'item_name', 'number', 'start_time', 'end_time', 'description', 'item_image'
        ]


class ProductApplicationForm(forms.ModelForm):
    message = forms.CharField(
        label="メッセージ",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "受け取り希望：いつでも可、場所日時相談",
                "maxlength": 255,
            }
        ),
    )

    class Meta:
        model = ProductApplication
        fields = ["message"]
