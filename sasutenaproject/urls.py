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

from django.conf import settings
from django.conf.urls.static import static
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
    
    # ログイン画面
    path("admin/", admin.site.urls),
    path('login/', include(('login.urls', 'login'), namespace='login')),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    
    # ログイン後の画面
    path('dashboard/', include('dashboard.urls')),
    
    path('product/', include(('product.urls', 'product'), namespace='product')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
