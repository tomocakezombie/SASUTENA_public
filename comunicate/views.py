from collections import OrderedDict

from django import forms as django_forms
from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import MessageEditForm, MessageForm
from .models import Message
from product.models import Product

User = get_user_model()


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
    all_users = User.objects.exclude(pk=user.pk).order_by("username")
    products_by_user = {}
    for product in Product.objects.filter(user__in=all_users).order_by("item_name"):
        products_by_user.setdefault(product.user_id, []).append(product)

    message_queryset = (
        Message.objects.filter(Q(send_user=user) | Q(receive_user=user), delete_flag=False)
        .select_related("send_user", "receive_user", "item")
        .order_by("-send_time")
    )

    conversations = OrderedDict()
    for msg in message_queryset:
        key = _conversation_key(user, msg)
        if key not in conversations:
            counterpart = msg.receive_user if msg.send_user == user else msg.send_user
            conversations[key] = {
                "counterpart": counterpart,
                "item": msg.item,
                "unread": msg.receive_user == user and not msg.read_flag,
                "latest": msg,
            }
        else:
            if msg.receive_user == user and not msg.read_flag:
                conversations[key]["unread"] = True

    requested_username = request.GET.get("user")
    requested_item_id = request.GET.get("item")
    requested_thread_url = ""

    user_threads = OrderedDict()

    for counterpart in all_users:
        user_threads[counterpart.pk] = {
            "counterpart": counterpart,
            "threads": OrderedDict(),
            "unread": False,
            "products": list(products_by_user.get(counterpart.pk, [])),
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

        preview_author = "あなた" if latest_message.send_user == user else latest_message.send_user.username

        entry = user_threads.setdefault(
            counterpart.pk,
            {"counterpart": counterpart, "threads": OrderedDict(), "unread": False},
        )

        thread_key = thread_item.pk if thread_item else None
        if thread_key not in entry["threads"]:
            entry["threads"][thread_key] = {
                "item": thread_item,
                "thread_url": thread_url,
                "preview_author": preview_author,
                "preview": latest_message.message_content or "",
                "latest_time": latest_message.send_time,
                "unread": data["unread"],
            }
        else:
            if data["unread"]:
                entry["threads"][thread_key]["unread"] = True

        if data["unread"]:
            entry["unread"] = True

        if requested_username and counterpart.username == requested_username:
            same_item = bool(thread_item) and requested_item_id and str(thread_item.pk) == requested_item_id
            if requested_item_id and same_item:
                requested_thread_url = thread_url
            elif not requested_item_id and not thread_item:
                requested_thread_url = thread_url

    user_entries = []
    for entry in user_threads.values():
        threads = list(entry["threads"].values())
        entry_data = {
            "counterpart": entry["counterpart"],
            "threads": threads,
            "has_threads": bool(threads),
            "unread": entry["unread"],
            "products": entry["products"],
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


def _apply_read_flags(user, messages_qs):
    unread_ids = []
    for msg in messages_qs:
        if msg.receive_user == user and not msg.read_flag:
            unread_ids.append(msg.pk)
            msg.read_flag = True
    if unread_ids:
        Message.objects.filter(pk__in=unread_ids).update(read_flag=True)


@login_required
def conversation_detail(request, username, item_id=None):
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        return redirect("comunicate:conversation_list")

    thread_item = None
    if item_id is not None:
        thread_item = get_object_or_404(Product, pk=item_id)
        if thread_item.user_id != target_user.pk:
            raise Http404("指定された商品はこのユーザーのものではありません。")

    messages_qs = list(_conversation_queryset(request.user, target_user, thread_item))
    _apply_read_flags(request.user, messages_qs)

    if messages_qs and thread_item is None:
        thread_item = messages_qs[0].item

    initial = {"item": thread_item}
    form = MessageForm(initial=initial)
    form.fields["item"].queryset = Product.objects.filter(user=target_user).order_by("item_name")
    if thread_item or request.headers.get("x-requested-with") == "XMLHttpRequest":
        form.fields["item"].widget = django_forms.HiddenInput()

    if request.method == "POST":
        form = MessageForm(request.POST, initial=initial)
        form.fields["item"].queryset = Product.objects.filter(user=target_user).order_by("item_name")
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
    }
    return render(request, template_name, context)


def _conversation_redirect(message, current_user):
    counterpart = message.receive_user if message.send_user == current_user else message.send_user
    if message.item_id:
        return reverse(
            "comunicate:conversation_detail_item",
            kwargs={"username": counterpart.username, "item_id": message.item_id},
        )
    return reverse("comunicate:conversation_detail", kwargs={"username": counterpart.username})


@login_required
def message_edit(request, pk):
    message = get_object_or_404(Message, pk=pk, delete_flag=False)
    if message.send_user != request.user:
        return redirect("comunicate:conversation_list")

    if request.method == "POST":
        form = MessageEditForm(request.POST, instance=message)
        if form.is_valid():
            message.record_edit(form.cleaned_data["message_content"])
            django_messages.success(request, "メッセージを更新しました。")
            return redirect(_conversation_redirect(message, request.user))
    else:
        form = MessageEditForm(instance=message)

    return render(request, "comunicate/message_edit.html", {"form": form, "message": message})


@login_required
def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk, delete_flag=False)
    if message.send_user != request.user:
        return redirect("comunicate:conversation_list")

    message.mark_as_deleted()
    django_messages.success(request, "メッセージを削除しました。")
    return redirect(_conversation_redirect(message, request.user))

