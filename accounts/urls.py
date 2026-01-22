from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.accounts_root, name="root"),
    path("evaluate/", views.producer_evaluation_overview, name="producer_evaluation_overview"),
    path("my_page/", views.my_page, name="my_page"),
    path("my_page/bio/", views.update_profile_bio, name="update_profile_bio"),
    path("my_page/status/", views.status_summary, name="status_summary"),
    path("users/<str:username>/", views.profile_detail, name="profile_detail"),
    path("users/<str:username>/evaluate/", views.evaluate, name="evaluate"),
    path("settings/", views.settings, name="settings"),
    path("history/",views.history,name="history"),
]
