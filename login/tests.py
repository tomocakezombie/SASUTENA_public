from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile

from . import views
from .forms import PasswordResetConfirmForm, PasswordResetRequestForm, SignupForm
from .models import AccountRequest, PasswordResetToken


class LoginAppTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="password", role="consumer")

    def test_accountrequest_generate_verification_code(self):
        """login.models.AccountRequest の検証コード生成を検証。"""
        """
        # テスト関数名: test_accountrequest_generate_verification_code
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: 検証コード生成
        # 入力値: AccountRequest インスタンス
        # 期待結果: 検証コードと有効期限が生成される
        """
        ar = AccountRequest.objects.create(username="req1", email="a@b.com", password="pw")
        code = ar.generate_verification_code()
        self.assertIsNotNone(ar.verification_code)
        self.assertEqual(code, ar.verification_code)
        self.assertIsNotNone(ar.verification_expires_at)
        self.assertGreater(ar.verification_expires_at, timezone.now())

    def test_passwordresettoken_validity_and_mark_used(self):
        """login.models.PasswordResetToken の有効性と使用済み挙動を検証。"""
        """
        # テスト関数名: test_passwordresettoken_validity_and_mark_used
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: トークンの有効性と使用済みフラグ
        # 入力値: PasswordResetToken インスタンス
        # 期待結果: トークンが正しく無効化される
        """
        token = PasswordResetToken.objects.create(user=self.user, token="tok", expires_at=timezone.now() + timedelta(hours=1))
        self.assertTrue(token.is_valid())
        token.mark_used()
        self.assertIsNotNone(token.used_at)
        self.assertFalse(token.is_valid())

    def test_signupform_password_mismatch(self):
        """login.forms.SignupForm のパスワード不一致バリデーションを検証。"""
        """
        # テスト関数名: test_signupform_password_mismatch
        # 対象URL: なし（フォームテスト）
        # テスト観点: パスワード確認の一致
        # 入力値: password="a", confirm_password="b"
        # 期待結果: フォームが無効になる
        """
        data = {"username": "x", "email": "x@x.com", "role": "consumer", "password": "a", "confirm_password": "b"}
        form = SignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_password_reset_request_form_lookup(self):
        """login.forms.PasswordResetRequestForm のユーザー照合処理を検証。"""
        """
        # テスト関数名: test_password_reset_request_form_lookup
        # 対象URL: なし（フォームテスト）
        # テスト観点: ユーザー名とメールアドレスの一致
        # 入力値: 正しい組み合わせと間違った組み合わせ
        # 期待結果: 正しい場合は有効、間違った場合は無効
        """
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": self.user.email})
        self.assertTrue(form.is_valid())
        bad = PasswordResetRequestForm(data={"username": self.user.username, "email": "nope@example.com"})
        self.assertFalse(bad.is_valid())


class LoginUrlResolutionTests(TestCase):
    """login.urls 内の named URL が正しく逆引きできるか検証するテストケース。"""

    def test_login_url_reverse(self):
        """login:login → /login/"""
        self.assertEqual(reverse("login:login"), "/login/")

    def test_logout_url_reverse(self):
        """login:logout → /login/logout/"""
        self.assertEqual(reverse("login:logout"), "/login/logout/")

    def test_index_url_reverse(self):
        """login:index → /login/index/"""
        self.assertEqual(reverse("login:index"), "/login/index/")

    def test_signup_url_reverse(self):
        """login:signup → /login/signup/"""
        self.assertEqual(reverse("login:signup"), "/login/signup/")

    def test_signup_done_url_reverse(self):
        """login:signup_done → /login/signup/done/"""
        self.assertEqual(reverse("login:signup_done"), "/login/signup/done/")

    def test_verify_url_reverse(self):
        """login:verify → /login/verify/"""
        self.assertEqual(reverse("login:verify"), "/login/verify/")

    def test_home_url_reverse(self):
        """login:home → /login/home/"""
        self.assertEqual(reverse("login:home"), "/login/home/")

    def test_password_change_url_reverse(self):
        """login:password_change → /login/password_change/"""
        self.assertEqual(reverse("login:password_change"), "/login/password_change/")

    def test_password_reset_confirm_url_reverse(self):
        """login:password_reset_confirm → /login/password_reset/<token>/"""
        self.assertEqual(
            reverse("login:password_reset_confirm", args=["sample-token"]),
            "/login/password_reset/sample-token/",
        )

    def test_consumer_portal_url_reverse(self):
        """login:consumer_portal → /login/consumer/portal/"""
        self.assertEqual(reverse("login:consumer_portal"), "/login/consumer/portal/")


class LoginViewAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.login_url = reverse("login:login")
        self.home_url = reverse("login:home")
        self.password_change_url = reverse("login:password_change")
        self.consumer_portal_url = reverse("login:consumer_portal")
        self.login_redirect_url = resolve_url(settings.LOGIN_URL)
        self.consumer = User.objects.create_user(username="cons", email="c@example.com", password="pw", role="consumer")
        self.producer = User.objects.create_user(username="prod", email="p@example.com", password="pw", role="producer")
        self.admin = User.objects.create_user(username="admin", email="a@example.com", password="pw", role="admin")

    def test_login_view_anonymous_get(self):
        """
        # テスト関数名: test_login_view_anonymous_get
        # 対象URL: login:login
        # テスト観点: 未認証ユーザーのアクセス状態
        # 入力値: 未ログイン
        # 期待結果: ステータスコード200
        """
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_view_redirects_consumer(self):
        """
        # テスト関数名: test_login_view_redirects_consumer
        # 対象URL: login:login
        # テスト観点: 認証済み利用者のリダイレクト
        # 入力値: consumerユーザー
        # 期待結果: consumerポータルへ302リダイレクト
        """
        self.client.force_login(self.consumer)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.consumer_portal_url)

    def test_login_view_redirects_producer(self):
        """
        # テスト関数名: test_login_view_redirects_producer
        # 対象URL: login:login
        # テスト観点: 認証済み生産者のリダイレクト
        # 入力値: producerユーザー
        # 期待結果: product:producer_product_list へ302リダイレクト
        """
        self.client.force_login(self.producer)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("product:producer_product_list"))

    def test_login_view_redirects_admin(self):
        """
        # テスト関数名: test_login_view_redirects_admin
        # 対象URL: login:login
        # テスト観点: 認証済み管理者のリダイレクト
        # 入力値: adminユーザー
        # 期待結果: adminPortal:admin_portal_list へ302リダイレクト
        """
        self.client.force_login(self.admin)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("adminPortal:admin_portal_list"))

    def test_home_requires_login(self):
        """
        # テスト関数名: test_home_requires_login
        # 対象URL: login:home
        # テスト観点: login_required デコレータの動作
        # 入力値: 未ログイン
        # 期待結果: ログイン画面へのリダイレクト
        """
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        expected = f"{self.login_redirect_url}?next={self.home_url}"
        self.assertEqual(response.url, expected)

    def test_home_authenticated_access(self):
        """
        # テスト関数名: test_home_authenticated_access
        # 対象URL: login:home
        # テスト観点: 認証済みアクセス時の表示確認
        # 入力値: consumerユーザー
        # 期待結果: ステータスコード200
        """
        self.client.force_login(self.consumer)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)

    def test_password_change_get(self):
        """
        # テスト関数名: test_password_change_get
        # 対象URL: login:password_change
        # テスト観点: パスワード再発行フォームの表示確認
        # 入力値: 未ログイン
        # 期待結果: ステータスコード200
        """
        response = self.client.get(self.password_change_url)
        self.assertEqual(response.status_code, 200)


class LoginViewAndModelBoundaryTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.consumer = User.objects.create_user(username="c1", email="c1@example.com", password="pw", role="consumer")

    def test_accountrequest_username_length_boundaries(self):
        """login.models.AccountRequest の username 長さ制約を境界値で検証。"""
        """
        # テスト関数名: test_accountrequest_username_length_boundaries
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: ユーザー名の長さ制限
        # 入力値: 長さ149, 150, 151のユーザー名
        # 期待結果: 長さ149と150は有効、151は無効
        """
        long_minus = "u" * 149
        long_exact = "u" * 150
        long_plus = "u" * 151
        ar1 = AccountRequest.objects.create(username=long_minus, email="a@b.com", password="pw")
        ar2 = AccountRequest.objects.create(username=long_exact, email="a@b.com", password="pw")
        over_limit = AccountRequest(username=long_plus, email="a@b.com", password="pw")
        with self.assertRaises(ValidationError):
            over_limit.full_clean()
        self.assertEqual(len(ar1.username), 149)
        self.assertEqual(len(ar2.username), 150)

    def test_passwordresettoken_expiry_property(self):
        """login.models.PasswordResetToken の期限切れ判定ロジックを検証。"""
        """
        # テスト関数名: test_passwordresettoken_expiry_property
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: トークンの有効期限切れ判定
        # 入力値: 現在時刻より過去の expires_at を持つトークン
        # 期待結果: is_expired が True になり、is_valid() が False を返す
        """
        token = PasswordResetToken.objects.create(user=self.consumer, token="t1", expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(token.is_expired)
        self.assertFalse(token.is_valid())


class SignupFormBehaviourTests(TestCase):
    def test_role_field_excludes_admin_choice(self):
        """login.forms.SignupForm で admin 選択肢が除外されることを検証。"""
        form = SignupForm()
        roles = {choice[0] for choice in form.fields["role"].choices}
        self.assertEqual(roles, {"producer", "consumer"})

    def test_save_combines_name_components(self):
        """login.forms.SignupForm の save で氏名が結合されることを検証。"""
        data = {
            "username": "signup_user",
            "email": "signup@example.com",
            "role": "producer",
            "password": "secret123",
            "confirm_password": "secret123",
            "family_name": "Smith",
            "given_name": "John",
            "family_name_kana": "SMITH",
            "given_name_kana": "JOHN",
        }
        form = SignupForm(data=data)
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        self.assertEqual(instance.full_name, "Smith John")
        self.assertEqual(instance.full_name_kana, "SMITH JOHN")

    def test_username_length_boundary_valid(self):
        """login.forms.SignupForm の username=150 文字境界値を検証。"""
        data = {
            "username": "u" * 150,
            "email": "signup@example.com",
            "role": "producer",
            "password": "secret123",
            "confirm_password": "secret123",
            "family_name": "Surname",
            "given_name": "Given",
            "family_name_kana": "SURNAME",
            "given_name_kana": "GIVEN",
        }
        form = SignupForm(data=data)
        self.assertTrue(form.is_valid())

    def test_username_length_boundary_invalid(self):
        """login.forms.SignupForm の username=151 文字でエラーとなる境界値を検証。"""
        data = {
            "username": "u" * 151,
            "email": "signup@example.com",
            "role": "producer",
            "password": "secret123",
            "confirm_password": "secret123",
            "family_name": "Surname",
            "given_name": "Given",
            "family_name_kana": "SURNAME",
            "given_name_kana": "GIVEN",
        }
        form = SignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class PasswordResetRequestFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="user1", email="user1@example.com", password="password", role="consumer")

    def test_sets_user_on_valid_lookup(self):
        """login.forms.PasswordResetRequestForm の正しい照合時に user 属性が設定される。"""
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": self.user.email})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.user, self.user)

    def test_user_without_email_is_rejected(self):
        """メール未登録ユーザーへの PasswordResetRequestForm 応答を検証。"""
        self.user.email = ""
        self.user.save(update_fields=["email"])
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": "missing@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_unknown_username_adds_error(self):
        """存在しないユーザー名で PasswordResetRequestForm がエラーを返すことを検証。"""
        form = PasswordResetRequestForm(data={"username": "unknown", "email": "unknown@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class PasswordResetConfirmFormTests(TestCase):
    def test_mismatched_passwords_raise_error(self):
        """login.forms.PasswordResetConfirmForm のパスワード不一致エラーを検証。"""
        form = PasswordResetConfirmForm(data={"new_password1": "abc12345", "new_password2": "xyz67890"})
        self.assertFalse(form.is_valid())
        self.assertIn("new_password2", form.errors)

    def test_matching_passwords_are_valid(self):
        """login.forms.PasswordResetConfirmForm の一致パスワードでフォームが有効になる。"""
        form = PasswordResetConfirmForm(data={"new_password1": "Matching123", "new_password2": "Matching123"})
        self.assertTrue(form.is_valid())

    def test_password_min_length_boundary(self):
        """login.forms.PasswordResetConfirmForm の最小長境界 (7文字) でエラーとなることを検証。"""
        form = PasswordResetConfirmForm(data={"new_password1": "Short77", "new_password2": "Short77"})
        self.assertFalse(form.is_valid())
        self.assertIn("new_password1", form.errors)


class RoleBasedLoginViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.producer = User.objects.create_user(username="producer", email="p@example.com", password="pw", role="producer")
        self.consumer = User.objects.create_user(username="consumer", email="c@example.com", password="pw", role="consumer")
        self.admin = User.objects.create_user(username="admin", email="a@example.com", password="pw", role="admin")

    def _get_success_url_for_user(self, user):
        request = self.factory.post(reverse("login:login"))
        request.user = user
        view = views.RoleBasedLoginView()
        view.setup(request)
        view.request = request
        return view.get_success_url()

    def test_producer_redirect(self):
        self.assertEqual(self._get_success_url_for_user(self.producer), reverse("product:producer_product_list"))

    def test_consumer_redirect(self):
        self.assertEqual(self._get_success_url_for_user(self.consumer), reverse("login:consumer_portal"))

    def test_admin_redirect(self):
        self.assertEqual(self._get_success_url_for_user(self.admin), reverse("adminPortal:admin_portal_list"))

    def test_default_redirect_for_unknown_role(self):
        unknown = get_user_model().objects.create_user(username="other", email="o@example.com", password="pw", role="unknown")
        self.assertEqual(self._get_success_url_for_user(unknown), reverse("login:index"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="test@example.com")
class SignupViewTests(TestCase):
    def setUp(self):
        self.url = reverse("login:signup")
        self.post_data = {
            "username": "signup_user",
            "email": "signup@example.com",
            "role": "consumer",
            "password": "SecurePass1",
            "confirm_password": "SecurePass1",
            "family_name": "Doe",
            "given_name": "Jane",
            "family_name_kana": "DOE",
            "given_name_kana": "JANE",
            "full_name": "",
            "full_name_kana": "",
        }

    def test_successful_submission_creates_account_request_and_sends_email(self):
        response = self.client.post(self.url, data=self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:verify"))

        account_request = AccountRequest.objects.get(username="signup_user")
        self.assertEqual(account_request.full_name, "Doe Jane")
        self.assertEqual(account_request.full_name_kana, "DOE JANE")
        self.assertIsNotNone(account_request.verification_code)

        session = self.client.session
        self.assertEqual(session.get("pending_email"), "signup@example.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(account_request.verification_code, mail.outbox[0].body)

    def test_invalid_submission_rerenders_form(self):
        bad = dict(self.post_data)
        bad["confirm_password"] = "mismatch"
        response = self.client.post(self.url, data=bad)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "confirm_password", "パスワードが一致しません。")
        self.assertEqual(AccountRequest.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)


class VerifySignupViewTests(TestCase):
    def setUp(self):
        self.url = reverse("login:verify")
        self.account_request = AccountRequest.objects.create(
            username="verify_user",
            email="verify@example.com",
            role="consumer",
            password="plainpass",
            verification_code="123456",
            verification_expires_at=timezone.now() + timedelta(minutes=5),
        )

    def _prepare_session(self):
        session = self.client.session
        session["pending_email"] = self.account_request.email
        session.save()

    def test_successful_verification_creates_user_and_profile(self):
        """login.models.AccountRequest のメール認証完了処理を検証。"""
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:login"))

        user = get_user_model().objects.get(username="verify_user")
        self.assertFalse(user.is_active)
        profile_exists = UserProfile.objects.filter(user=user).exists()
        self.assertTrue(profile_exists)

        self.account_request.refresh_from_db()
        self.assertTrue(self.account_request.is_verified)
        self.assertIsNone(self.account_request.verification_code)
        self.assertIsNone(self.account_request.verification_expires_at)

        session = self.client.session
        self.assertIsNone(session.get("pending_email"))

    def test_expired_code_adds_error(self):
        """login.models.AccountRequest の有効期限切れ判定。"""
        self.account_request.verification_expires_at = timezone.now() - timedelta(minutes=1)
        self.account_request.save(update_fields=["verification_expires_at"])
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("認証コードの有効期限が切れています。再度申請してください。", form.errors.get("code", []))

    def test_username_conflict_returns_form_error(self):
        """login.models.AccountRequest のユーザー名重複時のエラー処理。"""
        get_user_model().objects.create_user(username="verify_user", email="existing@example.com", password="pw", role="consumer")
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("このユーザー名は既に登録されています。", form.non_field_errors())

    def test_already_verified_request_is_rejected(self):
        """login.models.AccountRequest の再認証拒否を検証。"""
        self.account_request.is_verified = True
        self.account_request.save(update_fields=["is_verified"])
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("この申請は既にメール認証が完了しています。", form.non_field_errors())

    def test_invalid_code_shows_generic_error(self):
        """login.models.AccountRequest に保存されたコードとの不一致時動作。"""
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "000000"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("メールアドレスまたは認証コードが正しくありません。", form.non_field_errors())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="test@example.com")
class PasswordResetRequestViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="reset_user", email="reset@example.com", password="password", role="consumer")
        self.url = reverse("login:password_change")

    def test_creates_new_token_and_invalidates_previous(self):
        """login.models.PasswordResetToken の再発行時挙動を検証。"""
        previous_token = PasswordResetToken.objects.create(
            user=self.user,
            token="old-token",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        with patch("login.views.secrets.token_urlsafe", return_value="fresh-token"):
            response = self.client.post(self.url, data={"username": self.user.username, "email": self.user.email})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["reset_email_sent"])
        previous_token.refresh_from_db()
        self.assertIsNotNone(previous_token.used_at)

        new_token = PasswordResetToken.objects.get(token="fresh-token")
        self.assertEqual(new_token.user, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("fresh-token", mail.outbox[0].body)


class PasswordResetConfirmViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="confirm_user", email="confirm@example.com", password="password", role="consumer")
        self.url_base = "login:password_reset_confirm"

    def test_missing_token_marks_context_invalid(self):
        """login.models.PasswordResetToken の存在チェックを検証。"""
        response = self.client.get(reverse(self.url_base, args=["missing"]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["token_invalid"])
        self.assertFalse(response.context["token_expired"])

    def test_expired_token_sets_expired_flag(self):
        """login.models.PasswordResetToken の期限切れフラグを検証。"""
        expired_token = PasswordResetToken.objects.create(
            user=self.user,
            token="expired",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(reverse(self.url_base, args=[expired_token.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["token_invalid"])
        self.assertTrue(response.context["token_expired"])

    def test_valid_token_renders_form_with_username(self):
        """login.models.PasswordResetToken が有効な場合のレンダリング挙動。"""
        token = PasswordResetToken.objects.create(
            user=self.user,
            token="valid-token",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.get(reverse(self.url_base, args=[token.token]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["token_invalid"])
        self.assertEqual(response.context["username"], self.user.username)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_updates_password_and_marks_tokens(self):
        """login.models.PasswordResetToken のパスワード再設定完了処理を検証。"""
        active_token = PasswordResetToken.objects.create(
            user=self.user,
            token="active",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        other_token = PasswordResetToken.objects.create(
            user=self.user,
            token="other",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        response = self.client.post(
            reverse(self.url_base, args=[active_token.token]),
            data={"new_password1": "NewSecret1", "new_password2": "NewSecret1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["reset_completed"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecret1"))

        active_token.refresh_from_db()
        other_token.refresh_from_db()
        self.assertIsNotNone(active_token.used_at)
        self.assertIsNotNone(other_token.used_at)


class ConsumerPortalViewTests(TestCase):
    def setUp(self):
        self.url = reverse("login:consumer_portal")
        User = get_user_model()
        self.consumer = User.objects.create_user(username="consumer_portal", email="cp@example.com", password="password", role="consumer")
        self.producer = User.objects.create_user(username="producer_portal", email="pp@example.com", password="password", role="producer")
        self.admin = User.objects.create_user(username="admin_portal", email="ap@example.com", password="password", role="admin")
        self.login_redirect_url = resolve_url(settings.LOGIN_URL)

    def test_consumer_portal_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        expected = f"{self.login_redirect_url}?next={self.url}"
        self.assertEqual(response.url, expected)

    def test_consumer_receives_portal_template(self):
        self.client.force_login(self.consumer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_profile", response.context)
        self.assertIsNone(response.context["user_profile"])

    def test_consumer_portal_returns_existing_profile(self):
        profile = UserProfile.objects.create(user=self.consumer)
        self.client.force_login(self.consumer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user_profile"], profile)

    def test_producer_is_redirected_to_producer_list(self):
        self.client.force_login(self.producer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("product:producer_product_list"))

    def test_other_roles_redirect_to_home(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login:home"))