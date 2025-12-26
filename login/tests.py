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
        ar = AccountRequest.objects.create(username="req1", email="a@b.com", password="pw")
        code = ar.generate_verification_code()
        self.assertIsNotNone(ar.verification_code)
        self.assertEqual(code, ar.verification_code)
        self.assertIsNotNone(ar.verification_expires_at)
        self.assertGreater(ar.verification_expires_at, timezone.now())

    def test_passwordresettoken_validity_and_mark_used(self):
        token = PasswordResetToken.objects.create(user=self.user, token="tok", expires_at=timezone.now() + timedelta(hours=1))
        self.assertTrue(token.is_valid())
        token.mark_used()
        self.assertIsNotNone(token.used_at)
        self.assertFalse(token.is_valid())

    def test_signupform_password_mismatch(self):
        data = {"username": "x", "email": "x@x.com", "role": "consumer", "password": "a", "confirm_password": "b"}
        form = SignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_password_reset_request_form_lookup(self):
        form = PasswordResetRequestForm(data={"username": self.user.username, "email": self.user.email})
        self.assertTrue(form.is_valid())
        # wrong email
        bad = PasswordResetRequestForm(data={"username": self.user.username, "email": "nope@example.com"})
        self.assertFalse(bad.is_valid())


class LoginViewAndModelBoundaryTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.consumer = User.objects.create_user(username="c1", email="c1@example.com", password="pw", role="consumer")

    def test_accountrequest_username_length_boundaries(self):
        # username max 150 in model; test boundaries
        long_minus = "u" * 149
        long_exact = "u" * 150
        long_plus = "u" * 151
        ar = AccountRequest.objects.create(username=long_exact, email="a@b.com", password="pw")
        self.assertEqual(len(ar.username), 150)

    def test_passwordresettoken_expiry_property(self):
        from django.utils import timezone
        from datetime import timedelta
        token = PasswordResetToken.objects.create(user=self.consumer, token="t1", expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(token.is_expired)
        self.assertFalse(token.is_valid())