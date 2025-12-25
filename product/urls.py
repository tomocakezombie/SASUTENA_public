from django.urls import path
from . import views

app_name = "product"

urlpatterns = [
    path('create/', views.product_create, name='product_create'),
    path('list/', views.product_list, name='product_list'),
    path('delete/<int:pk>/', views.product_delete, name='product_delete'),
    path('producer/<int:pk>/complete/', views.product_complete, name='product_complete'),
    path('consumer/list/', views.consumer_product_list, name='consumer_product_list'),
    path('producer/list/', views.producer_product_list, name='producer_product_list'),
    path('comment/<int:comment_id>/update/', views.product_comment_update, name='comment_update'),
    path('comment/<int:comment_id>/delete/', views.product_comment_delete, name='comment_delete'),
    path('<int:pk>/', views.product_detail, name='product_detail'),  # Assuming you have a product_detail view
]