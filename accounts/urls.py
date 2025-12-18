from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("my_page/", views.my_page, name="my_page"),
    path("my_page/bio/", views.update_profile_bio, name="update_profile_bio"),
    path("users/<str:username>/", views.profile_detail, name="profile_detail"),
    path("users/<str:username>/evaluate/", views.evaluate, name="evaluate"),
    path("settings/", views.settings, name="settings"),
]
