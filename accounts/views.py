from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import UserProfile


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
