from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from .forms import ProductForm
from .models import Product

@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            return redirect('product_list')
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