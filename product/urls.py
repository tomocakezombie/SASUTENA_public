from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.product_create, name = 'product_create'),
    path('list/', views.product_list, name = 'product_list'),
    path('delete/<int:pk>/', views.product_delete, name = 'product_delete'),
    path('consumer/list/', views.consumer_product_list, name='consumer_product_list'),
]