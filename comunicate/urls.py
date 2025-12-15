from django.urls import path

from . import views

app_name = "comunicate"

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("thread/<str:username>/", views.conversation_detail, name="conversation_detail"),
    path(
        "thread/<str:username>/item/<int:item_id>/",
        views.conversation_detail,
        name="conversation_detail_item",
    ),
    path("message/<int:pk>/edit/", views.message_edit, name="message_edit"),
    path("message/<int:pk>/delete/", views.message_delete, name="message_delete"),
]
