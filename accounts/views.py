import json

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.conf import settings

from .forms import UserEvaluationForm, userSettings
from .models import UserEvaluation, UserProfile

from login.models import AccountRequest
from product.models import ProductApplication, Product
from collections import defaultdict


User = get_user_model()


def _render_evaluation_forbidden(request, reason):
	return render(
		request,
		"accounts/evaluation_forbidden.html",
		{"reason": reason},
		status=403,
	)


def accounts_root(request):
	"""Redirect /accounts/ to login or the user's dashboard."""
	if not request.user.is_authenticated:
		return redirect("login:login")
	return redirect("accounts:my_page")


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


def build_status_rows(user):
	"""Return per-role status summaries for the profile dashboard."""
	role = getattr(user, "role", "")
	rows = []
	if role == "producer":
		products = Product.objects.filter(user=user)
		pending_products = products.filter(
			valid=False,
			rejected_at__isnull=True,
		).filter(Q(admin_comment__isnull=True) | Q(admin_comment=""))
		rows.append({"label": "承認待ち出品", "value": pending_products.count(), "unit": "件"})
		rows.append({"label": "承認済み出品", "value": products.filter(valid=True).count(), "unit": "件"})
		rows.append({"label": "取引完了", "value": products.filter(completed=True).count(), "unit": "件"})
		orders_count = ProductApplication.objects.filter(product__user=user).count()
		rows.append({"label": "受注（申込み）件数", "value": orders_count, "unit": "件"})
	elif role == "consumer":
		applications = ProductApplication.objects.filter(user=user)
		rows.append({"label": "申込み済み出品", "value": applications.count(), "unit": "件"})
		rows.append({
			"label": "承認済み申込み",
			"value": applications.filter(apply_status=ProductApplication.STATUS_APPROVED).count(),
			"unit": "件",
		})
		rows.append({
			"label": "承認待ち申込み",
			"value": applications.filter(apply_status=ProductApplication.STATUS_PENDING).count(),
			"unit": "件",
		})
		rows.append({
			"label": "取引完了",
			"value": applications.filter(
				Q(product__completed=True)
				| Q(apply_status=ProductApplication.STATUS_APPROVED)
			).count(),
			"unit": "件",
		})
	elif role == "admin":
		pending_requests = AccountRequest.objects.filter(is_approved=False).count()
		rejected_products = Product.objects.filter(rejected_at__isnull=False).count()
		unapproved_products = Product.objects.filter(valid=False, rejected_at__isnull=True).count()
		registered_users = User.objects.filter(is_active=True).count()
		rows = [
			{"label": "ユーザーの承認待ち申請", "value": pending_requests, "unit": "件"},
			{"label": "ユーザー及び出品物の却下済み", "value": rejected_products, "unit": "件"},
			{"label": "未承認の出品", "value": unapproved_products, "unit": "件"},
			{"label": "登録済みユーザー", "value": registered_users, "unit": "名"},
		]
	return rows


@login_required
def my_page(request):
	"""Display the logged-in user's own profile page."""
	profile, _ = UserProfile.objects.get_or_create(  # safeguard in case profile is missing
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
	evaluations = UserEvaluation.objects.filter(
		target_user_id=request.user
	).select_related("from_user_id__profile").order_by("created_at")  

 
	user_comments = defaultdict(list)
	latest_times = {}
	last_scores = {}

	for e in evaluations:
		user_comments[e.from_user_id].append(e)
		latest_times[e.from_user_id] = e.created_at
		last_scores[e.from_user_id] = e.score

    # ユーザーごとのリストに変換
	received_evaluations_by_user = []
	for user, entries in user_comments.items():
		received_evaluations_by_user.append({
            "user": user,
            "entries": entries,
            "latest": latest_times[user],
            "last_score": last_scores[user],
        })


	if getattr(request.user, "role", "") == "admin":
		return redirect("adminPortal:my_page")

	return render(
		request,
		"accounts/my_profile.html",
		{
			"user_obj": request.user,
			"profile": profile,
			"rating_average": evaluation_stats["avg"],
			"rating_count": evaluation_stats["count"],
			"rating_stars": _build_star_states(evaluation_stats["avg"]),
   			"received_evaluations_by_user": received_evaluations_by_user,
			"status_rows": build_status_rows(request.user),
		},
	)

@login_required
def profile_detail(request, username):
	"""Display another user's profile. Redirect to my_page if it is yourself."""
	target_user = get_object_or_404(User, username=username)

	if request.user.is_authenticated and target_user.id == request.user.id:
		return redirect("accounts:my_page")

	profile = UserProfile.objects.filter(user=target_user).first()
	evaluation_stats = UserEvaluation.objects.filter(target_user_id=target_user).aggregate(
		avg=Avg("score"),
		count=Count("id"),
	)

	target_user_role = getattr(target_user, "role", "")
	status_rows = build_status_rows(target_user) if target_user_role != "admin" else []

	next_url = request.GET.get("next")
	allowed_hosts = set(getattr(settings, "ALLOWED_HOSTS", []))
	allowed_hosts.add(request.get_host())
	allowed_hosts.add("")  # allow relative paths
	if next_url and url_has_allowed_host_and_scheme(
		next_url,
		allowed_hosts=allowed_hosts,
		require_https=request.is_secure(),
	):
		back_url = next_url
	else:
		user_role = getattr(request.user, "role", "")
		if user_role == "producer":
			back_url = reverse("product:producer_product_list")
		elif user_role == "consumer":
			back_url = reverse("product:consumer_product_list")
		else:
			back_url = reverse("product:consumer_product_list")

	if profile and not profile.publish_profile:
		return render(
			request,
			"accounts/profile_private.html",
			{
				"target_user": target_user,
				"profile": profile,
				"back_url": back_url,
			},
			status=403,
		)

	request_user_role = getattr(request.user, "role", "")
	can_evaluate = (
		request.user.is_authenticated
		and request.user.username != target_user.username
		and request_user_role == "consumer"
		and target_user_role == "producer"
	)

	return render(
		request,
		"accounts/user_profile.html",
		{
			"target_user": target_user,
			"profile": profile,
			"rating_average": evaluation_stats["avg"],
			"rating_count": evaluation_stats["count"],
			"rating_stars": _build_star_states(evaluation_stats["avg"]),
			"back_url": back_url,
			"evaluated_back_url": request.get_full_path(),
			"can_evaluate": can_evaluate,
			"status_rows": status_rows,
		},
	)

@login_required
def settings(request):
	"""Display and handle the user settings page."""
	profile, _created = UserProfile.objects.get_or_create(
		user=request.user,
		defaults={
			"nick_name": request.user.username,
			"publish_profile": True,
			"mail_allow": True,
		},
	)

	old_icon_name = profile.icon_image.name if profile.icon_image else None

	profile_form = userSettings(
		request.POST if request.method == "POST" and request.POST.get("form_type") == "profile" else None,
		request.FILES if request.method == "POST" and request.POST.get("form_type") == "profile" else None,
		instance=profile,
	)
	password_form = PasswordChangeForm(
		user=request.user,
		data=request.POST if request.method == "POST" and request.POST.get("form_type") == "password" else None,
	)
	for field in password_form.fields.values():
		existing_classes = field.widget.attrs.get("class", "")
		field.widget.attrs["class"] = (existing_classes + " form-control").strip()
		field.widget.attrs.pop("autofocus", None)

	if request.method == "POST":
		form_type = request.POST.get("form_type")
		if form_type == "profile" and profile_form.is_valid():
			updated_profile = profile_form.save(commit=False)
			icon_field = profile_form.cleaned_data.get("icon_image")

			if icon_field is False:
				updated_profile.icon_image = None
			if not updated_profile.nick_name:
				updated_profile.nick_name = request.user.username

			# 管理用メモの保存
			updated_profile.memo = profile_form.cleaned_data.get("memo", "")

			updated_profile.save()
			profile_form.save_m2m()

			new_icon_name = updated_profile.icon_image.name if updated_profile.icon_image else None
			if old_icon_name and old_icon_name != new_icon_name:
				default_storage.delete(old_icon_name)
			messages.success(request, "プロフィールを更新しました。")
			return redirect("accounts:settings")
		if form_type == "password" and password_form.is_valid():
			user = password_form.save()
			update_session_auth_hash(request, user)
			messages.success(request, "パスワードを更新しました。")
			return redirect("accounts:settings")
		elif form_type == "password":
			# フォームエラーをターミナルに出力
			print("PasswordChangeForm errors:", password_form.errors)
		if form_type not in {"profile", "password"}:
			messages.error(request, "送信内容を処理できませんでした。改めてお試しください。")

	return render(
		request,
		"accounts/settings.html",
		{
			"profile": profile,
			"profile_form": profile_form,
			"password_form": password_form,
		},
	)

@login_required
@require_POST
def update_profile_bio(request):
	"""Persist profile bio updates triggered from the profile page."""
	profile, _created = UserProfile.objects.get_or_create(
		user=request.user, #user=request.user のレコード取得
		defaults={
			"nick_name": request.user.username,
			"publish_profile": True,
			"mail_allow": True,
		},
	)

	if request.headers.get("Content-Type", "").startswith("application/json"):
		try:
			payload = json.loads(request.body.decode("utf-8") or "{}")
		except json.JSONDecodeError:
			payload = {}
	else:
		payload = request.POST

	raw_bio = payload.get("content_profile", "")
	if not isinstance(raw_bio, str):
		raw_bio = ""

	new_bio = raw_bio.strip()
	if len(new_bio) > 100:
		return JsonResponse({"success": False, "error": "BIO_TOO_LONG"}, status=400)

	profile.content_profile = new_bio
	profile.save(update_fields=["content_profile"])

	return JsonResponse({"success": True, "bio": new_bio})

@login_required
def evaluate(request, username):
	"""Render and process the form used to evaluate another user."""
	target_user = get_object_or_404(User, username=username)

	if target_user == request.user:
		return _render_evaluation_forbidden(request, "自分を評価することはできません。")

	request_user_role = getattr(request.user, "role", "")
	target_user_role = getattr(target_user, "role", "")

	if request_user_role != "consumer":
		return _render_evaluation_forbidden(request, "評価は消費者のみが行えます。")

	if target_user_role != "producer":
		return _render_evaluation_forbidden(request, "生産者以外は評価対象にできません。")

	requested_next = request.POST.get("next") or request.GET.get("next")
	allowed_hosts = set(getattr(settings, "ALLOWED_HOSTS", []))
	allowed_hosts.add(request.get_host())
	allowed_hosts.add("")
	if requested_next and not url_has_allowed_host_and_scheme(
		requested_next,
		allowed_hosts=allowed_hosts,
		require_https=request.is_secure(),
	):
		requested_next = None

	evaluation = UserEvaluation.objects.filter(
		target_user_id=target_user,
		from_user_id=request.user,
	).first()

	if request.method == "POST":
		form = UserEvaluationForm(request.POST, instance=evaluation)
		if form.is_valid():
			evaluation = form.save(commit=False)
			evaluation.target_user_id = target_user
			evaluation.from_user_id = request.user
			evaluation.save()
			messages.success(request, f"{target_user.username} さんへの評価を保存しました。")
			if requested_next:
				return redirect(requested_next)
			return redirect("accounts:profile_detail", username=target_user.username)
	else:
		form = UserEvaluationForm(instance=evaluation)

	return render(
		request,
		"accounts/evaluate.html",
		{
			"target_user": target_user,
			"form": form,
			"current_score": evaluation.score if evaluation else None,
			"current_comment": evaluation.comment if evaluation else None,
			"next_url": requested_next,
		},
	)


@login_required
def producer_evaluation_overview(request):
	"""Show producer list with entry points for submitting evaluations."""
	if getattr(request.user, "role", "") != "consumer":
		return HttpResponseForbidden("このページには消費者のみアクセスできます。")

	producer_list = (
		User.objects.filter(role="producer")
		.select_related("profile")
		.annotate(average_score=Avg("evaluations__score"), rating_count=Count("evaluations__id"))
		.order_by("username")
	)

	evaluation_history = (
		UserEvaluation.objects.filter(from_user_id=request.user)
		.select_related("target_user_id", "target_user_id__profile")
		.order_by("-id")
	)

	return render(
		request,
		"accounts/producer_evaluation_overview.html",
		{
			"producer_list": producer_list,
			"evaluation_history": evaluation_history,
		},
	)



@login_required
def history(request):
	user = request.user
	role = getattr(user, "role", "")

	summary = {}
	applied_list = []
	completed_list = []
	received_list = []
	product_list = []
	pending_list = []
 
	# views.py で追加
	STATUS_DISPLAY = {
		ProductApplication.STATUS_PENDING: "pending",
		ProductApplication.STATUS_APPROVED: "completed",
		ProductApplication.STATUS_DECLINED: "declined",
		ProductApplication.STATUS_CANCELLED: "cancelled",
	}
 
	if role == "consumer":
		applied_qs = ProductApplication.objects.filter(user=user).select_related("product")
		applied_list = applied_qs.order_by("-apply_time")
		completed_qs = applied_qs.filter(
			Q(product__completed=True) | Q(apply_status=ProductApplication.STATUS_APPROVED)
		).order_by("-apply_time")
		pending_qs = applied_qs.filter(
			product__completed=False,
			apply_status=ProductApplication.STATUS_PENDING,
		).order_by("-apply_time")

		completed_list = list(completed_qs)
		pending_list = list(pending_qs)

		def _derive_status(application):
			if application.product and application.product.completed:
				return "completed"
			return STATUS_DISPLAY.get(application.apply_status, "pending")

		for app in completed_list:
			app.status_str = _derive_status(app)

		for app in pending_list:
			app.status_str = _derive_status(app)

		summary = {
			"completed": len(completed_list),
			"applied": len(pending_list),
		}

	elif role == "producer":
		my_products = Product.objects.filter(user=user)
		product_list = my_products.order_by("-created_at")

		# 商品ごとの申し込み数
		product_counts = (
			ProductApplication.objects.filter(product__in=my_products)
			.values("product")
			.annotate(apply_count=Count("apply_id"))
		)

		# 辞書化してアクセスしやすく
		apply_count_dict = {item["product"]: item["apply_count"] for item in product_counts}

		# 商品に属性としてセット
		for product in product_list:
			product.apply_count = apply_count_dict.get(product.item_id, 0)
			statuses = []

			if not product.valid and product.admin_comment:
				statuses.append("rejected")
			if product.valid:
				statuses.append("approved")
			if product.completed:
				statuses.append("completed")
			if product.apply_count > 0:
				statuses.append("received")
			if product.valid == False and product.admin_comment is None and product.apply_count == 0:
				statuses.append("registered")


			product.status = statuses




		summary = {
			"registered": my_products.count(),
			"approved": my_products.filter(valid=True).count(),
			"rejected": my_products.filter(valid=False, admin_comment__isnull=False).count(),
			"received": sum(apply_count_dict.values()),
			"completed": my_products.filter(completed=True).count(),
		}

		received_list = (
			ProductApplication.objects.filter(product__in=my_products)
			.select_related("product", "user")
			.order_by("-apply_time")
		)

	return render(request, "accounts/history.html", {
		"role": role,
		"summary": summary,
		"applied_list": applied_list,
		"completed_list": completed_list,
    	"pending_list": pending_list, 
		"received_list": received_list,
		"product_list": product_list,
	})


@login_required
def status_summary(request):
	"""Return JSON payload containing status rows for the current user."""
	if request.method != "GET":
		return JsonResponse({"detail": "METHOD_NOT_ALLOWED"}, status=405)
	rows = build_status_rows(request.user)
	return JsonResponse({"rows": rows})





