# This is Project views.py

import secrets
from datetime import timedelta

from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.urls import reverse
from django.shortcuts import get_object_or_404
from .forms import SignupForm, VerificationForm, PasswordResetRequestForm, PasswordResetConfirmForm
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import CustomUser, AccountRequest, PasswordResetToken

from .forms import SignupForm, VerificationForm
from .models import CustomUser, AccountRequest
from accounts.models import UserProfile

def helloworld(request):
    return HttpResponse("Hello Django!")


class RoleBasedLoginView(LoginView):
    template_name = "login/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return redirect_url

        user = self.request.user
        role = getattr(user, "role", "")

        if role == "producer":
            return reverse_lazy("product:producer_product_list")
        if role == "consumer":
            return reverse_lazy("login:consumer_portal")
        if role == "admin":
            return reverse_lazy("adminPortal:admin_portal_list")

        return reverse_lazy("login:index")

class SignupView(FormView):
    template_name = "login/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("login:verify")

    def form_valid(self, form):
        account_request = form.save()
        code = account_request.generate_verification_code()

        send_mail(
            subject="アカウント認証コード",
            message=(
                "以下の認証コードをサイトに入力してください\n"
                f"認証コード: {code}\n"
                "有効期限: 10分"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[account_request.email],
            fail_silently=False,
        )
        self.request.session["pending_email"] = account_request.email
        messages.info(self.request, "認証コードをメールに送信しました。コードを入力してください。")
        return redirect("login:verify")

# 確認コードの処理
class VerifySignupView(FormView):
    template_name = "login/verify.html"
    form_class = VerificationForm
    success_url = reverse_lazy("login:login")

    def get_initial(self):
        initial = super().get_initial()
        pending_email = self.request.session.get("pending_email")
        if pending_email:
            initial["email"] = pending_email
        return initial

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        code = form.cleaned_data["code"]

        try:
            account_request = AccountRequest.objects.get(email=email, verification_code=code)
        except AccountRequest.DoesNotExist:
            form.add_error(None, "メールアドレスまたは認証コードが正しくありません。")
            return self.form_invalid(form)

        if not account_request.verification_expires_at or account_request.verification_expires_at < timezone.now():
            form.add_error("code", "認証コードの有効期限が切れています。再度申請してください。")
            return self.form_invalid(form)

        if CustomUser.objects.filter(username=account_request.username).exists():
            form.add_error(None, "このユーザー名は既に登録されています。")
            return self.form_invalid(form)

        # 1. loginアプリの CustomUser を作成・保存
        new_user = CustomUser.objects.create_user(
            username=account_request.username,
            email=account_request.email,
            password=account_request.password, # create_userを使うとハッシュ化されます
            role=account_request.role,
            is_active=False,
            first_name=account_request.full_name,
        )

        # 2. accountsアプリの UserProfile を作成して紐付け
        UserProfile.objects.create(
            user=new_user,
            name=account_request.full_name,
            nick_name=account_request.username,
            publish_profile=True,
            mail_allow=True
        )

        # 3. リクエスト済みデータのクリーンアップ
        account_request.is_approved = False
        account_request.save()
        
        account_request.save(update_fields=["is_approved", "verification_code", "verification_expires_at"])
        self.request.session.pop("pending_email", None)
        messages.success(self.request, "アカウント登録申請が完了しました。\n 管理者が承認次第、ログイン可能になります。")
        success_url = reverse_lazy("login:index")  
        return super().form_valid(form)


class PasswordResetRequestView(FormView):
    template_name = "login/password_change.html"
    form_class = PasswordResetRequestForm

    def form_valid(self, form):
        user = form.user

        # invalidate previous unused tokens
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

        token_value = secrets.token_urlsafe(32)
        expiry = timezone.now() + timedelta(hours=1)
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token_value,
            expires_at=expiry,
        )

        reset_url = self.request.build_absolute_uri(
            reverse("login:password_reset_confirm", args=[reset_token.token])
        )

        message_lines = [
            f"{user.username} さん", "",
            "パスワード再発行の申請を受け付けました。以下のリンクから仮パスワード設定ページにアクセスし、\n新しいパスワードを設定してください。",
            "",
            reset_url,
            "",
            "リンクの有効期限は1時間です。期限を過ぎた場合は再度申請してください。",
            "",
            "このメールに心当たりがない場合は破棄してください。",
            "",
            f"Sasutena Project {self.request.get_host()}",
        ]

        send_mail(
            subject="【Sasutena】パスワード再設定リンク",
            message="\n".join(message_lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        context = self.get_context_data(
            form=self.form_class(),
            reset_email_sent=True,
            email=user.email,
        )
        return self.render_to_response(context)


class PasswordResetConfirmView(FormView):
    template_name = "login/password_reset_confirm.html"
    form_class = PasswordResetConfirmForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        token_value = kwargs.get("token", "")
        self.token_object = PasswordResetToken.objects.filter(token=token_value).select_related("user").first()

    def dispatch(self, request, *args, **kwargs):
        if not self.token_object:
            return self.render_to_response(
                self.get_context_data(token_invalid=True, form=self.form_class())
            )
        if not self.token_object.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    token_invalid=True,
                    token_expired=self.token_object.is_expired,
                    form=self.form_class(),
                )
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("token_invalid", False)
        context.setdefault("token_expired", False)
        context["username"] = self.token_object.user.username if self.token_object else ""
        return context

    def form_valid(self, form):
        user = self.token_object.user
        new_password = form.cleaned_data["new_password1"]
        user.set_password(new_password)
        user.save(update_fields=["password"])
        self.token_object.mark_used()

        # invalidate other tokens
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).exclude(pk=self.token_object.pk).update(used_at=timezone.now())

        context = self.get_context_data(reset_completed=True, form=self.form_class())
        return self.render_to_response(context)
    
@login_required
def consumer_portal(request):
    role = getattr(request.user, "role", "")

    if role == "consumer":
        return render(
            request,
            "login/consumer_portal.html",
            {
                "user_profile": getattr(request.user, "userprofile", None),
            },
        )

    # 以下ありえないケース

    if role == "producer":
        return redirect("product:producer_product_list")
    
    return redirect("login:home")
