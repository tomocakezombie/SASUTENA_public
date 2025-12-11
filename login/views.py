# This is Project views.py

from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from .forms import SignupForm, VerificationForm
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from .models import CustomUser, AccountRequest
from accounts.models import UserProfile

# class homeView(TemplateView):
#     # template_name = "home.html"
#     return TemplateView.as_view(template_name="home.html")

def helloworld(request):
    return HttpResponse("Hello Django!")

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

        # 1. まず loginアプリの CustomUser を作成・保存
        new_user = CustomUser.objects.create_user(
            username=account_request.username,
            email=account_request.email,
            password=account_request.password, # create_userを使うとハッシュ化されます
            role=account_request.role
        )

        # 2. 次に accountsアプリの UserProfile を作成して紐付け
        # 設計書にある初期値があればここで設定
        UserProfile.objects.create(
            user=new_user,
            nick_name=account_request.username, # 初期値としてユーザー名を入れるなど
            publish_profile=True,
            mail_allow=True
        )

        # 3. リクエスト済みデータのクリーンアップ
        account_request.is_approved = True
        account_request.save()
        
        # return redirect('login:login_success') # ログイン画面やダッシュボードへ
        account_request.save(update_fields=["is_approved", "verification_code", "verification_expires_at"])
        self.request.session.pop("pending_email", None)
        messages.success(self.request, "アカウント登録申請が完了しました。ログインしてください。")
        success_url = reverse_lazy("login:index")  
        return super().form_valid(form)