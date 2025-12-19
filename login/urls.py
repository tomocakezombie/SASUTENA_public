from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from . import views

app_name = "login"

index_view = TemplateView.as_view(template_name="login/index.html")
home_view = TemplateView.as_view(template_name="login/home.html")

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name="login/login.html"), name="login"),
    path('logout/', auth_views.LogoutView.as_view(
        template_name="login/logout.html"
    ), name="logout"),
    path('index/', index_view, name="index"),
    path('signup/', views.SignupView.as_view(), name="signup"),
    path('signup/done/', TemplateView.as_view(template_name="login/signup_done.html"), name="signup_done"),
    path('verify/', views.VerifySignupView.as_view(), name="verify"),
    path('home/', login_required(home_view), name="home"),
    path('password_change/', views.PasswordResetRequestView.as_view(), name="password_change"),
]
