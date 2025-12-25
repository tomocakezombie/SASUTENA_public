from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .forms import ProductForm, ProductApplicationForm, ProductCommentForm
from .models import Product, ProductApplication, ProductComment
from .mentions import sync_comment_mentions

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
            return redirect('product:producer_product_list')
        print("フォームは無効です")
        return render(request, 'product/product_create.html', {'form': form})
    else:
        form = ProductForm()

    return render(request, 'product/product_create.html', {'form': form})

@login_required
def product_list(request):
    return redirect('product:producer_product_list')

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 自分の商品以外は削除させない
    if product.user != request.user:
        return redirect('product:producer_product_list')

    product.delete()
    return redirect('product:producer_product_list')

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
    
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    is_owner = product.user == request.user
    user_role = getattr(request.user, 'role', '')
    consumer_roles = {'consumer', 'guest', 'user'}
    applications = product.applications.select_related('user')
    comments = (
        product.comments
        .filter(delete_flag=False)
        .select_related('user')
        .prefetch_related('mentions__mentioned_user')
    )
    user_application = applications.filter(user=request.user).first()

    can_apply = (
        (user_role in consumer_roles)
        and not is_owner
        and product.publish
        and product.valid
        and not product.completed
    )

    application_form = ProductApplicationForm() if can_apply and not user_application else None
    comment_form = ProductCommentForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'comment':
            comment_form = ProductCommentForm(request.POST)
            if comment_form.is_valid():
                comment = ProductComment.objects.create(
                    product=product,
                    user=request.user,
                    content=comment_form.cleaned_data['content'],
                )
                sync_comment_mentions(comment)
                messages.success(request, 'コメントを投稿しました。')
                return redirect('product:product_detail', pk=product.pk)
        else:
            if not can_apply:
                messages.warning(request, 'この商品には申込みできません。')
                return redirect('product:product_detail', pk=product.pk)

            if user_application:
                messages.info(request, 'すでに申込み済みです。')
                return redirect('product:product_detail', pk=product.pk)

            application_form = ProductApplicationForm(request.POST)
            if application_form.is_valid():
                ProductApplication.objects.create(
                    product=product,
                    user=request.user,
                    hope_time=application_form.cleaned_data.get('hope_time'),
                    quantity=application_form.cleaned_data.get('quantity') or 1,
                    message=application_form.cleaned_data.get('message', ''),
                )
                messages.success(request, '申込みを送信しました。生産者からの連絡をお待ちください。')
                return redirect('product:product_detail', pk=product.pk)

    return render(request, 'product/product_detail.html', {
        'product': product,
        'is_owner': is_owner,
        'applications': applications.order_by('-apply_time'),
        'show_apply_button': can_apply and user_application is None,
        'application_form': application_form,
        'user_application': user_application,
        'comments': comments,
        'comment_form': comment_form,
    })


@login_required
@require_POST
def product_comment_update(request, comment_id):
    comment = get_object_or_404(ProductComment, pk=comment_id, delete_flag=False)

    if comment.user != request.user:
        messages.warning(request, '自分のコメントのみ編集できます。')
        return redirect('product:product_detail', pk=comment.product.pk)

    form = ProductCommentForm(request.POST, instance=comment)
    if form.is_valid():
        comment.content = form.cleaned_data['content']
        comment.edit_flag = True
        comment.save(update_fields=['content', 'edit_flag'])
        sync_comment_mentions(comment)
        messages.success(request, 'コメントを更新しました。')
    else:
        messages.error(request, 'コメントの更新に失敗しました。内容を確認してください。')

    return redirect('product:product_detail', pk=comment.product.pk)


@login_required
@require_POST
def product_comment_delete(request, comment_id):
    comment = get_object_or_404(ProductComment, pk=comment_id, delete_flag=False)

    if comment.user != request.user:
        messages.warning(request, '自分のコメントのみ削除できます。')
        return redirect('product:product_detail', pk=comment.product.pk)

    comment.delete_flag = True
    comment.save(update_fields=['delete_flag'])
    messages.success(request, 'コメントを削除しました。')
    return redirect('product:product_detail', pk=comment.product.pk)