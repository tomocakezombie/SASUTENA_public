from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from .models import AccountRequest, PasswordResetToken
from .forms import SignupForm, PasswordResetRequestForm
from django.contrib.auth import get_user_model


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
        with self.assertRaises(ValueError):
            ar3 = AccountRequest.objects.create(username=long_plus, email="a@b.com", password="pw")
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