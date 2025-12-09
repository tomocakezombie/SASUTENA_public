from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProductForm

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
