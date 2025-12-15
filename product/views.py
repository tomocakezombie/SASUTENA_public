from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from .forms import ProductForm
from .models import Product

@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        print("フォーム送信を受け取りました")
        if form.is_valid():
            print("フォームは有効です")
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            return redirect('producer_product_list')
        print("フォームは無効です")
        return render(request, 'product/product_create.html', {'form': form})
    else:
        form = ProductForm()

    return render(request, 'product/product_create.html', {'form': form})

@login_required
def product_list(request):
    products = Product.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'product/product_list.html', {'products': products})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 自分の商品以外は削除させない
    if product.user != request.user:
        return redirect('product_list')

    product.delete()
    return redirect('product_list')

@login_required
def consumer_product_list(request):
    products = Product.objects.filter(publish=True, valid=True, completed=False).order_by('-created_at')
    return render(request, 'product/consumer_product_list.html', {'products': products})

@login_required
def producer_product_list(request):
    user = request.user
    #自分の出品商品一覧
    my_products = Product.objects.filter(user=user).order_by('-created_at')
    #全体の出品商品一覧（承認前も含む）
    all_products = Product.objects.all().order_by('-created_at')
    
    return render(request, 'product/producer_product_list.html', {
        'my_products': my_products,
        'all_products': all_products,
    })