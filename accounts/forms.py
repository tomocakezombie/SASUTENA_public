from django import forms

from .models import UserProfile

class userSettings(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["nick_name", "publish_profile", "mail_allow", "icon_image"]