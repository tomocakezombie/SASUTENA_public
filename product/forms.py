from datetime import datetime, time

from django import forms
from django.conf import settings
from django.utils import timezone

from .models import Product, ProductApplication, ProductComment


class ProductForm(forms.ModelForm):
    start_date = forms.DateField(
        label="受け渡し開始日",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    start_clock = forms.TimeField(
        label="受け渡し開始時間",
        widget=forms.TimeInput(attrs={"type": "time", "step": "60"}, format="%H:%M"),
        input_formats=["%H:%M"],
        required=False,
    )
    end_date = forms.DateField(
        label="受け渡し終了日",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_clock = forms.TimeField(
        label="受け渡し終了時間",
        widget=forms.TimeInput(attrs={"type": "time", "step": "60"}, format="%H:%M"),
        input_formats=["%H:%M"],
        required=False,
    )

    class Meta:
        model = Product
        fields = ["item_name", "number", "description", "item_image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_inputs = [
            ("item_name", {"placeholder": "例：朝採れトマト10個入り"}),
            ("description", {"placeholder": "商品の状態や受渡条件、受け渡し場所などを記入", "rows": 4}),
        ]
        for field_name, extra_attrs in text_inputs:
            base_attrs = {"class": "form-control"}
            base_attrs.update(extra_attrs)
            self.fields[field_name].widget.attrs.update(base_attrs)

        number_attrs = {"class": "form-control", "min": 1}
        self.fields["number"].widget.attrs.update(number_attrs)

        date_attrs = {"class": "form-control", "placeholder": "yyyy/mm/dd"}
        self.fields["start_date"].widget.attrs.update(date_attrs)
        self.fields["end_date"].widget.attrs.update(date_attrs.copy())

        time_attrs = {"class": "form-control", "step": "60"}
        self.fields["start_clock"].widget.attrs.update(time_attrs)
        self.fields["end_clock"].widget.attrs.update(time_attrs.copy())

        self.fields["item_image"].widget.attrs.update({"class": "form-control"})

        start_dt = getattr(self.instance, "start_time", None)
        if start_dt:
            localized = timezone.localtime(start_dt) if timezone.is_aware(start_dt) else start_dt
            self.fields["start_date"].initial = localized.date()
            self.fields["start_clock"].initial = localized.time().replace(second=0, microsecond=0)
        end_dt = getattr(self.instance, "end_time", None)
        if end_dt:
            localized = timezone.localtime(end_dt) if timezone.is_aware(end_dt) else end_dt
            self.fields["end_date"].initial = localized.date()
            self.fields["end_clock"].initial = localized.time().replace(second=0, microsecond=0)
        if self.fields["start_clock"].initial is None:
            self.fields["start_clock"].initial = time(hour=0, minute=0)
        if self.fields["end_clock"].initial is None:
            self.fields["end_clock"].initial = time(hour=23, minute=59)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        start_clock = cleaned_data.get("start_clock")
        end_date = cleaned_data.get("end_date")
        end_clock = cleaned_data.get("end_clock")

        def _combine(date_value, time_value):
            if date_value is None or time_value is None:
                return None
            combined = datetime.combine(date_value, time_value)
            if settings.USE_TZ and timezone.is_naive(combined):
                return timezone.make_aware(combined, timezone.get_current_timezone())
            return combined

        if start_clock:
            start_clock = start_clock.replace(second=0, microsecond=0)
        if end_clock:
            end_clock = end_clock.replace(second=0, microsecond=0)

        start_time_only = start_clock or time(hour=0, minute=0)
        end_time_only = end_clock or time(hour=23, minute=59)
        start_dt = _combine(start_date, start_time_only)
        end_dt = _combine(end_date, end_time_only)

        if start_dt and end_dt and end_dt < start_dt:
            self.add_error("end_date", "終了日時は開始日時以降を指定してください。")
            self.add_error("end_clock", "終了日時は開始日時以降を指定してください。")

        cleaned_data["start_clock"] = start_time_only
        cleaned_data["end_clock"] = end_time_only
        cleaned_data["start_time"] = start_dt
        cleaned_data["end_time"] = end_dt
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        product.start_time = self.cleaned_data.get("start_time")
        product.end_time = self.cleaned_data.get("end_time")
        if commit:
            product.save()
        return product


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


class ProductCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="コメントを投稿",
        max_length=511,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "コメントを入力してください",
                "maxlength": 511,
            }
        ),
    )

    class Meta:
        model = ProductComment
        fields = ["content"]

