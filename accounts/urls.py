from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("my_page/", views.my_page, name="my_page"),
    path("users/<str:username>/", views.profile_detail, name="profile_detail"),
    path("settings/", views.settings, name="settings"),
]
