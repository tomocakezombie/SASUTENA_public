from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        field = [
            'item_name', 'number', 'start_time', 'end_time', 'description', 'item_image'
        ]
        