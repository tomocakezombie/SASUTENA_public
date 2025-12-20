from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from login.models import AccountRequest
from product.models import Product
from comunicate.models import Message


def _ensure_admin(user):
    return getattr(user, "role", "") == "admin"


def _thread_key(message):
    user_ids = sorted([message.send_user_id, message.receive_user_id])
    item_key = message.item_id or 0
    return (*user_ids, item_key)


@login_required
def admin_portal_list(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    account_requests = AccountRequest.objects.order_by("-request_date").select_related()
    products = Product.objects.select_related("user").order_by("-created_at")

    return render(
        request,
        "adminPortal/admin_portal_list.html",
        {
            "account_requests": account_requests,
            "products": products,
        },
    )


@login_required
def admin_message_monitor(request):
    if not _ensure_admin(request.user):
        return redirect("login:index")

    messages_qs = (
        Message.objects.filter(delete_flag=False)
        .select_related("send_user", "receive_user", "item")
        .order_by("-send_time")
    )

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

                thread_messages = (
                    Message.objects.filter(detail_filters, delete_flag=False)
                    .select_related("send_user", "receive_user", "item")
                    .order_by("send_time")
                )

    context = {
        "threads": threads,
        "selected_thread": selected_thread,
        "thread_messages": thread_messages,
    }
    return render(request, "adminPortal/admin_message_monitor.html", context)


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
