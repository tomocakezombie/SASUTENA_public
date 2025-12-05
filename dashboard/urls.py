from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from . import views

app_name = "dashboard"

index_view = TemplateView.as_view(template_name="dashboard/index.html")
home_view = TemplateView.as_view(template_name="dashboard/home.html")

urlpatterns = [
    path('', views.test, name="index"),
    path('test/', views.test, name="test"),
]
