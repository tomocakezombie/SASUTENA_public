from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime, time

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from login.models import AccountRequest
from product.models import Product, TagType
from accounts.models import UserEvaluation, UserProfile
from comunicate.models import Message
from .forms import TagTypeForm


def _ensure_admin(user):
    return getattr(user, "role", "") == "admin"


def _attach_product_profiles(products):
    """Attach uploader profile information for admin product views."""
    if not products:
        return

    user_ids = {product.user_id for product in products}
    if not user_ids:
        return

    profiles = UserProfile.objects.filter(user_id__in=user_ids).select_related("user")
    profile_map = {profile.user_id: profile for profile in profiles}

    for product in products:
        product.owner_profile = profile_map.get(product.user_id)


def _thread_key(message):
    user_ids = sorted([message.send_user_id, message.receive_user_id])
    item_key = message.item_id or 0
    return (*user_ids, item_key)


def _parse_date(date_text, for_start=True):
    """Parse YYYY-MM-DD into an aware datetime at start or end of day."""
    if not date_text:
        return None
    try:
        date_obj = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return None
    boundary = time.min if for_start else time.max
    candidate = datetime.combine(date_obj, boundary)
    if timezone.is_naive(candidate):
        candidate = timezone.make_aware(candidate)
    return candidate


def _build_star_states(average_score):
    """Return per-star fill state for displaying ratings."""
    if average_score is None:
        return []
    avg_float = float(average_score)
    states = []
    for position in range(1, 6):
        if avg_float >= position:
            states.append("full")
        elif avg_float >= position - 0.5:
            states.append("half")
        else:
            states.append("empty")
    return states


@login_required
def admin_portal_list(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    account_requests = AccountRequest.objects.order_by("-request_date").select_related()
    products = list(Product.objects.select_related("user").order_by("-created_at"))
    _attach_product_profiles(products)

    return render(
        request,
        "adminPortal/admin_portal_list.html",
        {
            "account_requests": account_requests,
            "products": products,
        },
    )


@login_required
def manage_tags(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    form = TagTypeForm(request.POST or None)
    tag_list = TagType.objects.order_by("tag_name")

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "タグを追加しました。")
            return redirect("adminPortal:manage_tags")
        messages.error(request, "タグを追加できませんでした。内容を確認してください。")

    return render(
        request,
        "adminPortal/admin_manage_tags.html",
        {
            "form": form,
            "tag_list": tag_list,
        },
    )


@login_required
def admin_message_monitor(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    search_query = (request.GET.get("q") or "").strip()
    start_input = request.GET.get("start") or ""
    end_input = request.GET.get("end") or ""

    messages_qs = (
        Message.objects.filter(delete_flag=False)
        .select_related("send_user", "receive_user", "item")
        .order_by("-send_time")
    )

    if search_query:
        messages_qs = messages_qs.filter(
            Q(send_user__username__icontains=search_query)
            | Q(send_user__email__icontains=search_query)
            | Q(receive_user__username__icontains=search_query)
            | Q(receive_user__email__icontains=search_query)
            | Q(message_content__icontains=search_query)
            | Q(item__item_name__icontains=search_query)
        )

    start_dt = _parse_date(start_input, for_start=True)
    if start_dt:
        messages_qs = messages_qs.filter(send_time__gte=start_dt)

    end_dt = _parse_date(end_input, for_start=False)
    if end_dt:
        messages_qs = messages_qs.filter(send_time__lte=end_dt)

    user_cache = {}
    threads = []
    thread_index = {}

    for msg in messages_qs:
        user_cache.setdefault(msg.send_user_id, msg.send_user)
        user_cache.setdefault(msg.receive_user_id, msg.receive_user)
        key = _thread_key(msg)
        if key in thread_index:
            entry = thread_index[key]
            entry["message_count"] += 1
            continue

        user_a = user_cache[key[0]]
        user_b = user_cache[key[1]]
        item = msg.item
        thread_info = {
            "key": key,
            "user_a": user_a,
            "user_b": user_b,
            "item": item,
            "latest_message": msg,
            "message_count": 1,
        }
        threads.append(thread_info)
        thread_index[key] = thread_info

    selected_u1 = request.GET.get("u1")
    selected_u2 = request.GET.get("u2")
    selected_item = request.GET.get("item")

    thread_messages = []
    selected_thread = None

    if selected_u1 and selected_u2:
        try:
            user_ids = sorted([int(selected_u1), int(selected_u2)])
        except ValueError:
            user_ids = None

        item_key = 0
        if selected_item:
            try:
                item_key = int(selected_item)
            except ValueError:
                item_key = None

        if user_ids and item_key is not None:
            thread_key = (*user_ids, item_key)
            selected_thread = thread_index.get(thread_key)
            if selected_thread:
                detail_filters = Q(send_user_id=user_ids[0], receive_user_id=user_ids[1]) | Q(
                    send_user_id=user_ids[1], receive_user_id=user_ids[0]
                )
                if item_key:
                    detail_filters &= Q(item_id=item_key)
                else:
                    detail_filters &= Q(item__isnull=True)

                thread_filters = detail_filters & Q(delete_flag=False)
                if start_dt:
                    thread_filters &= Q(send_time__gte=start_dt)
                if end_dt:
                    thread_filters &= Q(send_time__lte=end_dt)

                thread_messages = (
                    Message.objects.filter(thread_filters)
                    .select_related("send_user", "receive_user", "item")
                    .order_by("send_time")
                )

    context = {
        "threads": threads,
        "selected_thread": selected_thread,
        "thread_messages": thread_messages,
        "search_query": search_query,
        "start_input": start_input,
        "end_input": end_input,
    }
    return render(request, "adminPortal/admin_message_monitor.html", context)


@login_required
def admin_my_page(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    profile, _created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "nick_name": request.user.username,
            "publish_profile": True,
            "mail_allow": True,
        },
    )

    evaluation_stats = UserEvaluation.objects.filter(target_user_id=request.user).aggregate(
        avg=Avg("score"),
        count=Count("id"),
    )

    return render(
        request,
        "adminPortal/admin_my_profile.html",
        {
            "user_obj": request.user,
            "profile": profile,
            "rating_average": evaluation_stats["avg"],
            "rating_count": evaluation_stats["count"],
            "rating_stars": _build_star_states(evaluation_stats["avg"]),
        },
    )


@login_required
@require_POST
def approve_account_request(request, pk):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    account_request = get_object_or_404(AccountRequest, pk=pk)

    if account_request.is_approved:
        messages.info(request, "既に承認済みの申請です。")
        return redirect("adminPortal:admin_portal_list")

    user_model = get_user_model()
    related_user = user_model.objects.filter(username=account_request.username).first()

    with transaction.atomic():
        account_request.is_approved = True
        account_request.save(update_fields=["is_approved"])

        if related_user and not related_user.is_active:
            related_user.is_active = True
            related_user.save(update_fields=["is_active"])

    messages.success(request, f"{account_request.username} の申請を承認しました。")
    return redirect("adminPortal:admin_portal_list")


@login_required
@require_POST
def toggle_product_visibility(request, pk):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    product = get_object_or_404(Product, pk=pk)

    if not product.valid and product.rejected_at:
        messages.warning(request, "まずは却下状態を解除してください。")
        return redirect("adminPortal:admin_portal_list")

    product.publish = not product.publish
    updates = ["publish"]

    if product.publish:
        product.valid = True
        product.rejected_at = None
        updates.extend(["valid", "rejected_at"])
        message = f"{product.item_name} を公開しました。"
    else:
        message = f"{product.item_name} を非公開にしました。"

    product.save(update_fields=updates)
    messages.success(request, message)
    return redirect("adminPortal:admin_portal_list")


@login_required
@require_POST
def reject_product(request, pk):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    product = get_object_or_404(Product, pk=pk)
    mode = request.POST.get("mode", "reject")

    if mode == "undo":
        if product.valid:
            messages.info(request, "この商品は既に承認状態です。")
            return redirect("adminPortal:admin_portal_list")

        product.valid = True
        product.rejected_at = None
        product.admin_comment = ""
        product.save(update_fields=["valid", "rejected_at", "admin_comment"])
        messages.success(request, f"{product.item_name} の却下を解除しました。")
        return redirect("adminPortal:admin_portal_list")

    reason = (request.POST.get("reason", "") or "").strip()
    if not reason:
        messages.error(request, "却下理由を入力してください。")
        return redirect("adminPortal:admin_portal_list")

    product.publish = False
    product.valid = False
    product.admin_comment = reason
    product.rejected_at = timezone.now()
    product.save(update_fields=["publish", "valid", "admin_comment", "rejected_at"])

    messages.success(request, f"{product.item_name} を却下しました。")
    return redirect("adminPortal:admin_portal_list")
