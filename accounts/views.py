import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import UserProfile
from .forms import userSettings


User = get_user_model()


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
	return render(
		request,
		"accounts/my_profile.html",
		{
			"user_obj": request.user,
			"profile": profile,
		},
	)

@login_required
def profile_detail(request, username):
	"""Display another user's profile. Redirect to my_page if it is yourself."""
	target_user = get_object_or_404(User, username=username)

	if request.user.is_authenticated and target_user.id == request.user.id:
		return redirect("accounts:my_page")

	profile = UserProfile.objects.filter(user=target_user).first()

	if profile and not profile.publish_profile:
		return HttpResponseForbidden("このプロフィールは非公開です")

	return render(
		request,
		"accounts/user_profile.html",
		{
			"target_user": target_user,
			"profile": profile,
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

	form = userSettings(
		request.POST or None,
		request.FILES or None,
		instance=profile,
	)

	if request.method == "POST" and form.is_valid():
		updated_profile = form.save(commit=False)
		if not updated_profile.nick_name:
			updated_profile.nick_name = request.user.username
		updated_profile.save()
		form.save_m2m()
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
		user=request.user,
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

