from django import forms

from .models import UserEvaluation, UserProfile


class userSettings(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["nick_name", "publish_profile", "mail_allow", "icon_image","content_profile"]
        widgets = {
            "icon_image": forms.FileInput(
                attrs={
                    "class": "visually-hidden",
                    "accept": "image/*",
                    "id": "iconImageInput",
                    "aria-label": "アイコン画像を選択",
                }
            ),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": 100}),  # 最大文字数指定
        }


class UserEvaluationForm(forms.ModelForm):
    score = forms.TypedChoiceField(
        label="評価 (1〜5)",
        choices=[(value, str(value)) for value in range(1, 6)],
        coerce=int,
        empty_value=None,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    comment = forms.CharField(
        label="コメント (任意)",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )

    class Meta:
        model = UserEvaluation
        fields = ["score", "comment"]