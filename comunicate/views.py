from collections import OrderedDict
from urllib.parse import urlencode

from django import forms as django_forms
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import MessageEditForm, MessageForm
from .models import Message
from accounts.models import UserProfile
from product.models import Product

User = get_user_model()


def _allowed_counterparts_for(current_user):
    qs = User.objects.exclude(pk=current_user.pk)
    if current_user.is_staff or current_user.is_superuser:
        return qs

    role = getattr(current_user, "role", None)
    if role == "admin":
        return qs

    producer_roles = {"producer", "proceduct"}
    base_filter = Q(is_staff=True) | Q(is_superuser=True) | Q(role="admin")
    if role in producer_roles:
        base_filter |= Q(role="consumer")
    elif role == "consumer":
        base_filter |= Q(role__in=producer_roles)

    return qs.filter(base_filter)


def _conversation_key(current_user, message):
    counterpart = message.receive_user if message.send_user == current_user else message.send_user
    return (counterpart.pk, message.item_id)


def _conversation_queryset(current_user, counterpart, thread_item):
    filters = Q(send_user=current_user, receive_user=counterpart) | Q(send_user=counterpart, receive_user=current_user)
    if thread_item:
        filters &= Q(item=thread_item)
    else:
        filters &= Q(item__isnull=True)
    return (
        Message.objects.filter(filters, delete_flag=False)
        .select_related("send_user", "receive_user", "item")
        .order_by("send_time")
    )


@login_required
def conversation_list(request):
    user = request.user
        
    allowed_users_qs = _allowed_counterparts_for(user).order_by("username")
    all_users = list(allowed_users_qs)

    allowed_user_ids = [counterpart.pk for counterpart in all_users]
    product_owner_ids = set(allowed_user_ids)
    product_owner_ids.add(user.pk)

    products_by_user = {}
    if product_owner_ids:
        product_queryset = (
            Product.objects.filter(user_id__in=product_owner_ids)
            .select_related("user")
            .order_by("item_name")
        )
        for product in product_queryset:
            products_by_user.setdefault(product.user_id, []).append(product)

    if allowed_user_ids:
        message_queryset = (
            Message.objects.filter(
                (
                    Q(send_user=user, receive_user_id__in=allowed_user_ids)
                    | Q(receive_user=user, send_user_id__in=allowed_user_ids)
                ),
                delete_flag=False,
            )
            .select_related("send_user", "receive_user", "item")
            .order_by("-send_time")
        )
    else:
        message_queryset = Message.objects.none()

    conversations = OrderedDict()
    for msg in message_queryset:
        key = _conversation_key(user, msg)
        if key not in conversations:
            counterpart = msg.receive_user if msg.send_user == user else msg.send_user
            conversations[key] = {
                "counterpart": counterpart,
                "item": msg.item,
                "unread_count": 1 if (msg.receive_user == user and not msg.read_flag) else 0,
                "latest": msg,
            }
        else:
            if msg.receive_user == user and not msg.read_flag:
                conversations[key]["unread_count"] += 1


    requested_username = request.GET.get("user")
    requested_item_id = request.GET.get("item")
    requested_thread_url = ""

    user_threads = OrderedDict()

    current_user_products = list(products_by_user.get(user.pk, []))
    include_own_products = bool(current_user_products) and (
        getattr(user, "role", None) in {"producer", "proceduct", "admin"}
        or user.is_staff
        or user.is_superuser
    )
    
    priority_user_ids = []
    for data in conversations.values():
        priority_user_ids.append(data["counterpart"].pk)
    priority_user_ids = list(dict.fromkeys(priority_user_ids))
    user_map = {u.pk: u for u in all_users}
    priority_users = [user_map[pk] for pk in priority_user_ids if pk in user_map]
    rest_users = [u for u in all_users if u.pk not in priority_user_ids]
    ordered_users = priority_users + rest_users
    
    profiles = UserProfile.objects.filter(user__in=ordered_users)
    profile_map = {p.user_id: p for p in profiles}

    for u in ordered_users:
        profile = profile_map.get(u.pk)
        if profile and profile.nick_name:
            u.display_name = profile.nick_name
        else:
            u.display_name = u.username



    for counterpart in ordered_users:
        combined_products = OrderedDict()
        for product in products_by_user.get(counterpart.pk, []):
            combined_products[product.pk] = product
        if include_own_products and counterpart.pk != user.pk:
            for product in current_user_products:
                combined_products.setdefault(product.pk, product)
        user_threads[counterpart.pk] = {
            "counterpart": counterpart,
            "threads": OrderedDict(),
            "unread_count": 0,
            "products": list(combined_products.values()),
        }

    for data in conversations.values():
        counterpart = data["counterpart"]
        thread_item = data["item"]
        latest_message = data["latest"]

        thread_url = (
            reverse(
                "comunicate:conversation_detail_item",
                kwargs={"username": counterpart.username, "item_id": thread_item.pk},
            )
            if thread_item
            else reverse("comunicate:conversation_detail", kwargs={"username": counterpart.username})
        )

        if latest_message.send_user == user:
            preview_author = "あなた"
        else:
            sender = latest_message.send_user
            profile = profile_map.get(sender.pk)
            preview_author = profile.nick_name if profile and profile.nick_name else sender.username


        entry = user_threads.setdefault(
            counterpart.pk,
            {"counterpart": counterpart, "threads": OrderedDict(), "unread": False},
        )

        thread_key = thread_item.pk if thread_item else None
        preview_text = (latest_message.message_content or "").strip()
        has_message = bool(preview_text)
        if thread_key not in entry["threads"]:
            entry["threads"][thread_key] = {
                "item": thread_item,
                "thread_url": thread_url,
                "preview_author": preview_author,
                "preview": preview_text,
                "has_message": has_message,
                "latest_time": latest_message.send_time,
                "unread_count": data["unread_count"],
            }
        else:
            entry["threads"][thread_key]["unread_count"] += data["unread_count"]
            entry["threads"][thread_key]["has_message"] = has_message or entry["threads"][thread_key].get("has_message", False)
            if has_message:
                entry["threads"][thread_key]["preview"] = preview_text
                entry["threads"][thread_key]["preview_author"] = preview_author
                entry["threads"][thread_key]["latest_time"] = latest_message.send_time
                
        entry["unread_count"] += data["unread_count"]


        if requested_username and counterpart.username == requested_username:
            same_item = bool(thread_item) and requested_item_id and str(thread_item.pk) == requested_item_id
            if requested_item_id and same_item:
                requested_thread_url = thread_url
            elif not requested_item_id and not thread_item:
                requested_thread_url = thread_url

    def _ensure_thread(entry, counterpart, product_obj):
        threads_map = entry["threads"]
        key = product_obj.pk if product_obj else None
        if key in threads_map:
            return
        if product_obj:
            thread_url = reverse(
                "comunicate:conversation_detail_item",
                kwargs={"username": counterpart.username, "item_id": product_obj.pk},
            )
        else:
            thread_url = reverse("comunicate:conversation_detail", kwargs={"username": counterpart.username})
        threads_map[key] = {
            "item": product_obj,
            "thread_url": thread_url,
            "preview_author": "",
            "preview": "",
            "has_message": False,
            "latest_time": None,
            "unread_count": 0,
        }

    for entry in user_threads.values():
        counterpart = entry["counterpart"]
        _ensure_thread(entry, counterpart, None)
        for product in entry.get("products", []):
            _ensure_thread(entry, counterpart, product)

    if requested_username and not requested_thread_url:
        target_entry = next(
            (entry for entry in user_threads.values() if entry["counterpart"].username == requested_username),
            None,
        )
        if target_entry:
            key = int(requested_item_id) if requested_item_id else None
            thread_data = target_entry["threads"].get(key)
            if thread_data:
                requested_thread_url = thread_data["thread_url"]

    user_entries = []
    for entry in user_threads.values():
        threads = list(entry["threads"].values())
        entry_data = {
            "counterpart": entry["counterpart"],
            "threads": threads,
            "has_threads": bool(threads),
            "unread_count": entry["unread_count"],
        }
        user_entries.append(entry_data)
        if not threads and requested_username == entry["counterpart"].username and not requested_thread_url:
            requested_thread_url = reverse(
                "comunicate:conversation_detail",
                kwargs={"username": entry["counterpart"].username},
            )

    initial_conversation_url = requested_thread_url or ""
    if not initial_conversation_url and user_entries:
        first_threads = user_entries[0]["threads"]
        if first_threads:
            initial_conversation_url = first_threads[0]["thread_url"]

    context = {
        "all_users": all_users,
        "user_entries": user_entries,
        "initial_conversation_url": initial_conversation_url,
        "initial_username": requested_username or (user_entries[0]["counterpart"].username if user_entries else ""),
    }
    return render(request, "comunicate/conversation_list.html", context)


@login_required
def conversation_detail(request, username, item_id=None):
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        return redirect("comunicate:conversation_list")

    if not (request.user.is_staff or request.user.is_superuser):
        if not _allowed_counterparts_for(request.user).filter(pk=target_user.pk).exists():
            raise Http404("このユーザーとは会話できません。")

    thread_item = None
    if item_id is not None:
        thread_item = get_object_or_404(Product, pk=item_id)
        if thread_item.user_id not in {target_user.pk, request.user.pk}:
            raise Http404("指定された商品は会話参加者のものではありません。")

    messages_qs = list(_conversation_queryset(request.user, target_user, thread_item))
    
    qs = Message.objects.filter(
        receive_user=request.user,
        send_user=target_user,         
        read_flag=False,
        delete_flag=False,
    )
    
    if thread_item is None:
        qs = qs.filter(item__isnull=True)
    else:
        qs = qs.filter(item=thread_item)

    qs.update(read_flag=True)
    

    if messages_qs and thread_item is None:
        thread_item = messages_qs[0].item

    initial = {"item": thread_item}
    participant_ids = {request.user.pk, target_user.pk}
    participant_profiles = UserProfile.objects.filter(user_id__in=participant_ids)
    icon_map = {}
    for profile in participant_profiles:
        if profile.icon_image:
            try:
                icon_map[profile.user_id] = profile.icon_image.url
            except ValueError:
                icon_map.setdefault(profile.user_id, "")
        else:
            icon_map.setdefault(profile.user_id, "")
    for user_id in participant_ids:
        icon_map.setdefault(user_id, "")
    for message in messages_qs:
        message.sender_icon_url = icon_map.get(message.send_user_id, "")

    form = MessageForm(initial=initial)
    form.fields["item"].queryset = Product.objects.filter(user_id__in=participant_ids).order_by("item_name")
    if thread_item or request.headers.get("x-requested-with") == "XMLHttpRequest":
        form.fields["item"].widget = django_forms.HiddenInput()

    if request.method == "POST":
        form = MessageForm(request.POST, initial=initial)
        form.fields["item"].queryset = Product.objects.filter(user_id__in=participant_ids).order_by("item_name")
        if thread_item or request.headers.get("x-requested-with") == "XMLHttpRequest":
            form.fields["item"].widget = django_forms.HiddenInput()
        if form.is_valid():
            Message.objects.create(
                send_user=request.user,
                receive_user=target_user,
                message_content=form.cleaned_data["message_content"],
                item=thread_item if thread_item else form.cleaned_data.get("item"),
            )
            return redirect(request.path)

    template_name = "comunicate/conversation_detail.html"
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        template_name = "comunicate/partials/conversation_thread.html"

    context = {
        "target_user": target_user,
        "messages": messages_qs,
        "form": form,
        "thread_item": thread_item,
        "thread_url": request.path,
        "participant_icons": icon_map,
    }
    return render(request, template_name, context)


def _conversation_redirect(message, current_user):
    counterpart = message.receive_user if message.send_user == current_user else message.send_user
    params = {"user": counterpart.username}
    if message.item_id:
        params["item"] = message.item_id
    base_url = reverse("comunicate:conversation_list")
    return f"{base_url}?{urlencode(params)}"


@login_required
@require_POST
def message_edit(request, pk):
    message = get_object_or_404(Message, pk=pk, delete_flag=False)
    if message.send_user != request.user:
        django_messages.warning(request, "自分が送信したメッセージのみ編集できます。")
        return redirect(_conversation_redirect(message, request.user))

    form = MessageEditForm(request.POST, instance=message)
    if form.is_valid():
        message.record_edit(form.cleaned_data["message_content"])
        django_messages.success(request, "メッセージを編集しました。")
    else:
        django_messages.error(request, "メッセージの編集に失敗しました。内容を確認してください。")

    return redirect(_conversation_redirect(message, request.user))


@login_required
@require_POST
def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk, delete_flag=False)
    if message.send_user != request.user:
        return redirect("comunicate:conversation_list")

    message.mark_as_deleted()
    django_messages.success(request, "メッセージを削除しました。")
    return redirect(_conversation_redirect(message, request.user))

