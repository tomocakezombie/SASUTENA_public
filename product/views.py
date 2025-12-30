import re

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q

from accounts.models import UserProfile

from .forms import ProductForm, ProductApplicationForm, ProductCommentForm
from .models import Product, ProductApplication, ProductComment
from .mentions import sync_comment_mentions

from django.utils import timezone
from datetime import timedelta

from adminPortal.models import ExpirationNoticeSetting
from django.core.paginator import Paginator

def _get_profiles_map(user_ids):
    """Return a mapping of user_id to profile for given users."""
    if not user_ids:
        return {}
    profiles = UserProfile.objects.filter(user_id__in=user_ids).select_related("user")
    return {profile.user_id: profile for profile in profiles}


def _attach_owner_profiles(*product_iterables):
    """Attach related user profiles to product instances for template use."""
    all_products = []
    for iterable in product_iterables:
        if iterable:
            all_products.extend(iterable)
    if not all_products:
        return

    user_ids = {product.user_id for product in all_products}
    if not user_ids:
        return

    profile_map = _get_profiles_map(user_ids)

    for product in all_products:
        product.owner_profile = profile_map.get(product.user_id)

def _attach_user_profiles(*iterables):
    all_objects = []
    for iterable in iterables:
        if iterable:
            all_objects.extend(iterable)
    if not all_objects:
        return

    user_ids = {obj.user_id for obj in all_objects}
    if not user_ids:
        return

    profile_map = _get_profiles_map(user_ids)

    for obj in all_objects:
        obj.user_profile = profile_map.get(obj.user_id)



def _redirect_for_role_mismatch(request, allowed_roles, info_message):
    """Redirect users whose role is not permitted for the current page."""
    role = getattr(request.user, "role", "")
    if role in allowed_roles:
        return None
    if info_message:
        messages.info(request, info_message)
    if role == "admin":
        return redirect("adminPortal:admin_portal_list")
    if role == "producer":
        return redirect("product:producer_product_list")
    if role == "consumer":
        return redirect("product:consumer_product_list")
    return redirect("login:index")

@login_required
def product_create(request):
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"producer"},
        "生産者専用のページです。",
    )
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        print("フォーム送信を受け取りました")
        if form.is_valid():
            print("フォームは有効です")
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            form.save_m2m()
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
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"producer"},
        "生産者専用のページです。",
    )
    if redirect_response:
        return redirect_response

    product = get_object_or_404(Product, pk=pk)

    # 自分の商品以外は削除させない
    if product.user != request.user:
        return redirect('product:producer_product_list')

    product.delete()
    return redirect('product:producer_product_list')


@login_required
@require_POST
def product_complete(request, pk):
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"producer"},
        "生産者専用のページです。",
    )
    if redirect_response:
        return redirect_response

    product = get_object_or_404(Product, pk=pk, user=request.user)

    if product.completed:
        messages.info(request, "すでに完了通知済みです。")
        return redirect("product:producer_product_list")

    if not (product.valid and product.publish):
        messages.warning(request, "承認済みかつ公開中の商品だけ完了通知できます。")
        return redirect("product:producer_product_list")

    product.completed = True
    product.completed_notified_at = timezone.now()
    product.save(update_fields=["completed", "completed_notified_at"])
    messages.success(request, f"{product.item_name} の取引完了を通知しました。")
    return redirect("product:producer_product_list")

@login_required
def consumer_product_list(request):
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"consumer"},
        "このページは消費者向けです。",
    )
    if redirect_response:
        return redirect_response
    base_queryset = (
        Product.objects.filter(publish=True, valid=True, completed=False)
        .select_related("user")
        .prefetch_related("tags")
    )

    search_query = (request.GET.get("q") or "").strip()
    search_tokens = [token for token in re.split(r"\s+", search_query) if token]
    if search_tokens:
        unique_tokens = []
        for token in search_tokens:
            if token not in unique_tokens:
                unique_tokens.append(token)
        search_tokens = unique_tokens

    quantity_min = request.GET.get("quantity_min")
    quantity_max = request.GET.get("quantity_max")
    start_after = request.GET.get("start_after")
    end_before = request.GET.get("end_before")

    filtered_products = base_queryset
    if search_tokens:
        for token in search_tokens:
            token_filter = (
                Q(item_name__icontains=token)
                | Q(description__icontains=token)
                | Q(user__username__icontains=token)
                | Q(tags__tag_name__icontains=token)
            )
            filtered_products = filtered_products.filter(token_filter)

    if quantity_min:
        try:
            quantity_min_value = int(quantity_min)
        except ValueError:
            quantity_min_value = None
        if quantity_min_value is not None:
            filtered_products = filtered_products.filter(number__gte=quantity_min_value)

    if quantity_max:
        try:
            quantity_max_value = int(quantity_max)
        except ValueError:
            quantity_max_value = None
        if quantity_max_value is not None:
            filtered_products = filtered_products.filter(number__lte=quantity_max_value)

    if start_after:
        filtered_products = filtered_products.filter(start_time__date__gte=start_after)

    if end_before:
        filtered_products = filtered_products.filter(end_time__date__lte=end_before)

    products = list(filtered_products.distinct().order_by('-created_at'))
    _attach_owner_profiles(products)
    filter_active = bool(
        search_tokens
        or quantity_min
        or quantity_max
        or start_after
        or end_before
    )

    expiring_products = get_expiring_products()
    _attach_owner_profiles(expiring_products)
    
    notice = ExpirationNoticeSetting.objects.filter(is_active=True).first()
    if notice:
        now = timezone.now()
    
        for product in expiring_products:
            profile = getattr(product, "owner_profile", None)

            if profile and profile.nick_name:
                user_display = f"{profile.nick_name}（{product.user.username}）"
            else:
                user_display = product.user.username

            product.notice_message = (
                notice.message
                .replace("{{user}}", user_display)
                .replace("{{item}}", product.item_name)
            )
            
    products_qs = Product.objects.all().order_by('-created_at')  # 必要に応じてフィルターを適用

    # ページネーション設定
    paginator = Paginator(products_qs, 10)  # 1ページあたり10件
    page_number = request.GET.get('page')  # URLパラメータ ?page=2 など
    page_obj = paginator.get_page(page_number)

                
    return render(
        request,
        'product/consumer_product_list.html',
        {
            'products': products,
            'search_query': search_query,
            'search_tokens': search_tokens,
            'quantity_min': quantity_min or "",
            'quantity_max': quantity_max or "",
            'start_after': start_after or "",
            'end_before': end_before or "",
            'filter_active': filter_active,
            'expiring_products': expiring_products,
            'expiration_notice': notice,
            'products': page_obj,
            'page_obj': page_obj, 
        },
    )

@login_required
def producer_product_list(request):
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"producer"},
        "このページは生産者向けです。",
    )
    if redirect_response:
        return redirect_response

    user = request.user
    #自分の出品商品一覧
    my_products = list(Product.objects.filter(user=user).order_by('-created_at'))
    #全体の出品商品一覧（承認前も含む）
    all_products = list(Product.objects.all().order_by('-created_at'))

    _attach_owner_profiles(my_products, all_products)
    
    expiring_products = get_expiring_products()
    _attach_owner_profiles(expiring_products)
    notice = ExpirationNoticeSetting.objects.filter(is_active=True).first()
    if notice:
        now = timezone.now()
            
        for product in expiring_products:
            profile = getattr(product, "owner_profile", None)

            if profile and profile.nick_name:
                user_display = f"{profile.nick_name}（{product.user.username}）"
            else:
                user_display = product.user.username

            product.notice_message = (
                notice.message
                .replace("{{user}}", user_display)
                .replace("{{item}}", product.item_name)
            )

        
    return render(request, 'product/producer_product_list.html', {
        'my_products': my_products,
        'all_products': all_products,
        'expiring_products': expiring_products,
        'expiration_notice': notice,
    })
    
@login_required
def product_detail(request, pk):
    redirect_response = _redirect_for_role_mismatch(
        request,
        {"consumer", "producer"},
        "商品の詳細は生産者・消費者のみ閲覧できます。",
    )
    if redirect_response:
        return redirect_response

    product = get_object_or_404(Product, pk=pk)
    _attach_owner_profiles([product])
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
    _attach_user_profiles(comments)
    user_application = applications.filter(user=request.user).first()

    can_apply = (
        (user_role in consumer_roles)
        and not is_owner
        and product.publish
        and product.valid
        and not product.completed
    )

    if user_role == "consumer" and not product.publish:
        messages.info(request, "非公開の商品にはアクセスできません。")
        return redirect("product:consumer_product_list")
    if user_role == "consumer" and not product.valid:
        messages.info(request, "承認前の商品にはアクセスできません。")
        return redirect("product:consumer_product_list")

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
        'applications': applications,
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


def get_expiring_products():
    now = timezone.now()

    notice = ExpirationNoticeSetting.objects.filter(is_active=True).first()
    days_before = notice.notify_days_before if notice else 1

    limit = now + timedelta(days=days_before)

    return Product.objects.filter(
        end_time__gte=now,
        end_time__lte=limit,
        show_expiration_notice=True,
        completed=False,
        publish=True,
        valid=True,
    ).select_related("user")


@login_required
def toggle_expiration_notice(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == "POST":
        product.show_expiration_notice = not product.show_expiration_notice
        product.save()
    return redirect("product:product_detail", pk=pk)

