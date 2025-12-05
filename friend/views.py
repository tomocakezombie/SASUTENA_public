from django.shortcuts import render
from django.shortcuts import render

from django.http import HttpResponse
from .models import Friend
from django.views.generic import ListView, DetailView

# クラスview
class FriendListView(ListView):
    model = Friend
    # template_name = 'friend_list.html'
    
class FriendDetailView(DetailView):
    model = Friend
    # template_name = 'friend_detail.html'

# 関数view
def helloworld(request):
    return HttpResponse("Hello Django!")

def one_hello(request):
    objects = Friend.objects.all()[0]
    html = f"<p>Hello {objects.name}!</p>"
    return HttpResponse(html)

def list_hello(request):
    objects = Friend.objects.all()
    html = ""
    for friend in objects:
        html += f"<p>Hello {friend.name}!</p>"
    return HttpResponse(html)