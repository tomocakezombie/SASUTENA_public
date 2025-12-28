from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
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


class LoginViewAndModelBoundaryTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.consumer = User.objects.create_user(username="c1", email="c1@example.com", password="pw", role="consumer")

    def test_accountrequest_username_length_boundaries(self):
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
        form = SignupForm()
        roles = {choice[0] for choice in form.fields["role"].choices}
        self.assertEqual(roles, {"producer", "consumer"})

    def test_save_combines_name_components(self):
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


class PasswordResetRequestFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="user1", email="user1@example.com", password="password", role="consumer")

    def test_sets_user_on_valid_lookup(self):
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": self.user.email})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.user, self.user)

    def test_user_without_email_is_rejected(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": "missing@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_unknown_username_adds_error(self):
        form = PasswordResetRequestForm(data={"username": "unknown", "email": "unknown@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class PasswordResetConfirmFormTests(TestCase):
    def test_mismatched_passwords_raise_error(self):
        form = PasswordResetConfirmForm(data={"new_password1": "abc12345", "new_password2": "xyz67890"})
        self.assertFalse(form.is_valid())
        self.assertIn("new_password2", form.errors)


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
        self.account_request.verification_expires_at = timezone.now() - timedelta(minutes=1)
        self.account_request.save(update_fields=["verification_expires_at"])
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("認証コードの有効期限が切れています。再度申請してください。", form.errors.get("code", []))

    def test_username_conflict_returns_form_error(self):
        get_user_model().objects.create_user(username="verify_user", email="existing@example.com", password="pw", role="consumer")
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("このユーザー名は既に登録されています。", form.non_field_errors())

    def test_already_verified_request_is_rejected(self):
        self.account_request.is_verified = True
        self.account_request.save(update_fields=["is_verified"])
        self._prepare_session()
        response = self.client.post(self.url, data={"email": self.account_request.email, "code": "123456"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("この申請は既にメール認証が完了しています。", form.non_field_errors())

    def test_invalid_code_shows_generic_error(self):
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
        response = self.client.get(reverse(self.url_base, args=["missing"]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["token_invalid"])
        self.assertFalse(response.context["token_expired"])

    def test_expired_token_sets_expired_flag(self):
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

    def test_consumer_receives_portal_template(self):
        self.client.force_login(self.consumer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_profile", response.context)
        self.assertIsNone(response.context["user_profile"])

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