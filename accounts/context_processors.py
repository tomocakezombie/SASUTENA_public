from .models import UserProfile


def current_user_profile(request):
    """Provide the authenticated user's profile for global templates."""
    profile = None
    if request.user.is_authenticated:
        profile, _created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "nick_name": request.user.username,
                "publish_profile": True,
                "mail_allow": True,
            },
        )
    return {"current_user_profile": profile}
