from django.urls import path

from . import views

app_name = "adminPortal"

urlpatterns = [
    path("", views.admin_portal_list, name="admin_portal_list"),
    path("requests/<int:pk>/approve/", views.approve_account_request, name="approve_account_request"),
    path("products/<int:pk>/toggle/", views.toggle_product_visibility, name="toggle_product_visibility"),
    path("products/<int:pk>/reject/", views.reject_product, name="reject_product"),
    path("messages/", views.admin_message_monitor, name="admin_message_monitor"),
]