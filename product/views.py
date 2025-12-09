from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProductForm
from django.shortcuts import get_object_or_404

@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit = False)
            product.user = request.user
            product.save()
            return redirect('product_list')
        else:
            form = ProductForm()
        return render(request, 'product/templates/product/product_create.html', {'form': form})

@login_required
def product_list(request):
    products = Product.objects.filter(user = request.user).order_by('-created_at')
    return render(request, 'product/temolates/product/product_list.html', {'product': products})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 自分の商品以外は削除させない
    if product.user != request.user:
        return redirect('product_list')

    product.delete()
    return redirect('product_list')
