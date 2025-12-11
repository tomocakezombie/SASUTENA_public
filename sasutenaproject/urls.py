"""
URL configuration for sasutenaproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

# ログイン済みか否かでリダイレクト先を変更
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("accounts:my_page")
    return redirect("login:login")

urlpatterns = [
    path("", root_redirect, name="root"),
    # path('polls/', include('polls.urls')),  
    # path("hello/", views.helloworld),
    # path('one', views.one_hello),
    # path('list/', views.FriendListView.as_view(), name="list"),
    # path('<int:pk>/', views.FriendDetailView.as_view(), name="detail"),
    
    # ログイン画面
    path("admin/", admin.site.urls),
    path('login/', include('login.urls')),
    path('accounts/', include('accounts.urls')),
    
    # ログイン後の画面
    path('dashboard/', include('dashboard.urls')),
    
    path('product/', include('product.urls')),
]
