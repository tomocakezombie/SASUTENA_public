from django.urls import path

from . import views

app_name = "adminPortal"

urlpatterns = [
    path("my-page/", views.admin_my_page, name="my_page"),
    path("", views.admin_portal_list, name="admin_portal_list"),
    path("products/<int:pk>/", views.admin_product_detail, name="admin_product_detail"),
    path("requests/<int:pk>/approve/", views.approve_account_request, name="approve_account_request"),
    path("requests/<int:pk>/unapprove/", views.unapprove_account_request, name="unapprove_account_request"),
    path("requests/<int:pk>/reject/", views.reject_account_request, name="reject_account_request"),
    path("products/auto-publish/toggle/", views.toggle_auto_publish_setting, name="toggle_auto_publish_setting"),
    path("products/<int:pk>/toggle/", views.toggle_product_visibility, name="toggle_product_visibility"),
    path("products/<int:pk>/reject/", views.reject_product, name="reject_product"),
    path("messages/", views.admin_message_monitor, name="admin_message_monitor"),
    path("tags/", views.manage_tags, name="manage_tags"),
    path("tags/<int:pk>/toggle-status/", views.toggle_tag_status, name="toggle_tag_status"),
    path("tags/<int:pk>/delete/", views.delete_tag, name="delete_tag"),
    path('expiration_notice/', views.manage_expiration_notice, name='manage_expiration_notice'),
]