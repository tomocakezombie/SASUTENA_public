import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import Avg, Count
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import UserEvaluationForm, userSettings
from .models import UserEvaluation, UserProfile


User = get_user_model()


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
def my_page(request):
	"""Display the logged-in user's own profile page."""
	profile, _created = UserProfile.objects.get_or_create(  # safeguard in case profile is missing
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
		"accounts/my_profile.html",
		{
			"user_obj": request.user,
			"profile": profile,
			"rating_average": evaluation_stats["avg"],
			"rating_count": evaluation_stats["count"],
			"rating_stars": _build_star_states(evaluation_stats["avg"]),
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

	if profile and not profile.publish_profile:
		return HttpResponseForbidden("このプロフィールは非公開です")

	return render(
		request,
		"accounts/user_profile.html",
		{
			"target_user": target_user,
			"profile": profile,
			"rating_average": evaluation_stats["avg"],
			"rating_count": evaluation_stats["count"],
			"rating_stars": _build_star_states(evaluation_stats["avg"]),
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

	form = userSettings(
		request.POST or None,
		request.FILES or None,
		instance=profile,
	)

	if request.method == "POST" and form.is_valid():
		updated_profile = form.save(commit=False)
		icon_field = form.cleaned_data.get("icon_image")

		if icon_field is False:
			updated_profile.icon_image = None
		if not updated_profile.nick_name:
			updated_profile.nick_name = request.user.username
		updated_profile.save()
		form.save_m2m()

		new_icon_name = updated_profile.icon_image.name if updated_profile.icon_image else None
		if old_icon_name and old_icon_name != new_icon_name:
			default_storage.delete(old_icon_name)
		return redirect("accounts:my_page")

	return render(
		request,
		"accounts/settings.html",
		{
			"profile": profile,
			"form": form,
		},
	)

@require_POST
@login_required
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
		return HttpResponseForbidden("自分を評価することはできません。")

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
		},
	)

