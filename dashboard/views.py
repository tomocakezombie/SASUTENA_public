from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
@login_required # ログイン前はアクセス不可
def test(request):
    return render(request, 'dashboard/test.html')