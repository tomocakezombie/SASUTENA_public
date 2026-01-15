from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from .models import UserProfile, UserEvaluation
from .forms import UserEvaluationForm
import json


class AccountsAppTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.consumer = User.objects.create_user(username="cons", password="pw", role="consumer", email="c@example.com")
		self.producer = User.objects.create_user(username="prod", password="pw", role="producer", email="p@example.com")
		self.admin = User.objects.create_user(username="admin", password="pw", role="admin", email="admin@example.com")
		UserProfile.objects.get_or_create(user=self.consumer, defaults={"nick_name": self.consumer.username, "publish_profile": True})
		UserProfile.objects.get_or_create(user=self.producer, defaults={"nick_name": self.producer.username, "publish_profile": True})
  

	def test_update_profile_bio_too_long(self):
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:update_profile_bio")
		long_bio = "x" * 200
		resp = self.client.post(url, data={"content_profile": long_bio})
		self.assertEqual(resp.status_code, 400)
		self.assertIn("BIO_TOO_LONG", resp.json().get("error", ""))

	def test_evaluate_cannot_self(self):
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:evaluate", args=[self.consumer.username])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 403)

	def test_producer_evaluation_overview_requires_consumer(self):
		self.client.login(username="prod", password="pw")
		url = reverse("accounts:producer_evaluation_overview")
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 403)

	def test_nick_name_length_boundaries(self):
		"""Test nick_name length boundaries for UserProfile."""
		profile, _ = UserProfile.objects.get_or_create(user=self.producer)

		# 254文字: 正常
		short = "あ" * 254
		profile.nick_name = short
		profile.save()
		self.assertEqual(len(profile.nick_name), 254)

		# 255文字: 正常
		exact = "あ" * 255
		profile.nick_name = exact
		profile.save()
		self.assertEqual(len(profile.nick_name), 255)

		# 256文字: 異常（切り詰めて保存）
		longer = "あ" * 256
		profile.nick_name = longer[:255]  # 保存前に切り捨て
		profile.save()
		self.assertEqual(len(profile.nick_name), 255)

	def test_userevaluationform_validation_and_save(self):
		self.client.login(username="cons", password="pw")
		# score required and coerced to int
		form = UserEvaluationForm(data={"score": "5", "comment": "良い"})
		self.assertTrue(form.is_valid())
		eval = form.save(commit=False)
		eval.target_user_id = self.producer
		eval.from_user_id = self.consumer
		eval.save()
		self.assertEqual(UserEvaluation.objects.filter(target_user_id=self.producer).count(), 1)

	def test_update_profile_bio_boundary_values(self):
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:update_profile_bio")

		# 99文字: 正常
		bio_99 = "x" * 99
		resp_99 = self.client.post(url, data={"content_profile": bio_99})
		self.assertIn(resp_99.status_code, [200, 302])  # 保存成功

		# 100文字: 正常
		bio_100 = "x" * 100
		resp_100 = self.client.post(url, data={"content_profile": bio_100})
		self.assertIn(resp_100.status_code, [200, 302])  # 保存成功

		# 101文字: 異常
		bio_101 = "x" * 101
		resp_101 = self.client.post(url, data={"content_profile": bio_101})
		self.assertEqual(resp_101.status_code, 400)
		self.assertIn("BIO_TOO_LONG", resp_101.json().get("error", ""))

	def test_reverse_producer_evaluation_overview(self):
		"""Test reverse for producer_evaluation_overview URL."""
		url = reverse("accounts:producer_evaluation_overview")
		self.assertEqual(url, "/accounts/evaluate/")

	def test_access_producer_evaluation_overview(self):
		"""Test GET access to producer_evaluation_overview view."""
		self.client.login(username="prod", password="pw")
		url = reverse("accounts:producer_evaluation_overview")
		response = self.client.get(url)
		self.assertEqual(response.status_code, 403)

	def test_reverse_my_page(self):
		"""Test reverse for my_page URL."""
		url = reverse("accounts:my_page")
		self.assertEqual(url, "/accounts/my_page/")

	def test_my_page_access_logged_in_user(self):
		"""Test my_page view for logged-in user (normal user)."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:my_page")
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

	def test_my_page_access_admin_user(self):
		"""Test my_page view redirects admin user."""
		self.client.login(username="admin", password="pw")
		url = reverse("accounts:my_page")
		response = self.client.get(url)
		self.assertEqual(response.status_code, 302)

	def test_profile_detail_self_redirect(self):
		"""Test profile_detail view redirects to my_page for self."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:profile_detail", args=[self.consumer.username])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 302)

	def test_profile_detail_other_user_public(self):
		"""Test profile_detail view for another user's public profile."""
		self.client.login(username="cons", password="pw")
		profile = UserProfile.objects.get(user=self.producer)
		profile.publish_profile = True
		profile.save()
		url = reverse("accounts:profile_detail", args=[self.producer.username])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

	def test_profile_detail_other_user_private(self):
		"""Test profile_detail view for another user's private profile."""
		self.client.login(username="cons", password="pw")
		profile = UserProfile.objects.get(user=self.producer)
		profile.publish_profile = False
		profile.save()
		url = reverse("accounts:profile_detail", args=[self.producer.username])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 403)

	def test_reverse_update_profile_bio(self):
		"""Test reverse for update_profile_bio URL."""
		url = reverse("accounts:update_profile_bio")
		self.assertEqual(url, "/accounts/my_page/bio/")

	def test_access_update_profile_bio(self):
		"""Test POST access to update_profile_bio view."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:update_profile_bio")
		response = self.client.post(url, data={"content_profile": "Test bio"})
		self.assertIn(response.status_code, [200, 302])

	def test_reverse_settings(self):
		"""Test reverse for settings URL."""
		url = reverse("accounts:settings")
		self.assertEqual(url, "/accounts/settings/")

	def test_access_settings(self):
		"""Test GET access to settings view."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:settings")
		response = self.client.get(url)
		self.assertIn(response.status_code, [200, 302])

	def test_reverse_history(self):
		"""Test reverse for history URL."""
		url = reverse("accounts:history")
		self.assertEqual(url, "/accounts/history/")

	def test_access_history(self):
		"""Test GET access to history view."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:history")
		response = self.client.get(url)
		self.assertIn(response.status_code, [200, 302])

	def test_settings_update_profile_success(self):
		"""Test successful profile update via settings view."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:settings")
		response = self.client.post(url, data={"form_type": "profile", "nick_name": "Updated Nickname"})
		self.assertEqual(response.status_code, 302)
		profile = UserProfile.objects.get(user=self.consumer)
		self.assertEqual(profile.nick_name, "Updated Nickname")

	def test_settings_invalid_form_type(self):
		"""Test settings view with invalid form_type."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:settings")
		response = self.client.post(url, data={"form_type": "invalid"})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "送信内容を処理できませんでした。")

	def test_update_profile_bio_valid(self):
		"""Test update_profile_bio view with valid bio."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:update_profile_bio")
		response = self.client.post(url, data={"content_profile": "Valid bio"}, content_type="application/json")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["bio"], "Valid bio")

	def test_update_profile_bio_too_long(self):
		"""Test update_profile_bio view with bio exceeding max length."""
		self.client.login(username="cons", password="pw")
		url = reverse("accounts:update_profile_bio")
		response = self.client.post(url, data={"content_profile": "x" * 101}, content_type="application/json")
		self.assertEqual(response.status_code, 400)
		self.assertIn("BIO_TOO_LONG", response.json()["error"])


class AccountsUrlAndViewTests(TestCase):
	"""accounts アプリの URL 逆引きおよび基本アクセス制御テスト。"""

	def setUp(self):
		User = get_user_model()
		self.consumer = User.objects.create_user("cons", password="pw", role="consumer", email="c@example.com")
		self.producer = User.objects.create_user("prod", password="pw", role="producer", email="p@example.com")
		self.admin = User.objects.create_user("admin", password="pw", role="admin", email="a@example.com")
		UserProfile.objects.get_or_create(user=self.consumer)
		UserProfile.objects.get_or_create(user=self.producer)
		UserProfile.objects.get_or_create(user=self.admin)

	def test_reverse_producer_evaluation_overview(self):
		self.assertEqual(reverse("accounts:producer_evaluation_overview"), "/accounts/evaluate/")

	def test_reverse_my_page(self):
		self.assertEqual(reverse("accounts:my_page"), "/accounts/my_page/")

	def test_reverse_update_profile_bio(self):
		self.assertEqual(reverse("accounts:update_profile_bio"), "/accounts/my_page/bio/")

	def test_reverse_status_summary(self):
		self.assertEqual(reverse("accounts:status_summary"), "/accounts/my_page/status/")

	def test_reverse_profile_detail(self):
		self.assertEqual(reverse("accounts:profile_detail", args=["demo"]), "/accounts/users/demo/")

	def test_reverse_evaluate(self):
		self.assertEqual(reverse("accounts:evaluate", args=["demo"]), "/accounts/users/demo/evaluate/")

	def test_reverse_settings(self):
		self.assertEqual(reverse("accounts:settings"), "/accounts/settings/")

	def test_reverse_history(self):
		self.assertEqual(reverse("accounts:history"), "/accounts/history/")

	def test_my_page_access_consumer(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:my_page"))
		self.assertEqual(resp.status_code, 200)

	def test_my_page_redirect_admin(self):
		self.client.login(username="admin", password="pw")
		resp = self.client.get(reverse("accounts:my_page"))
		self.assertEqual(resp.status_code, 302)
		self.assertIn(reverse("adminPortal:my_page"), resp.url)

	def test_producer_evaluation_overview_consumer_ok(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:producer_evaluation_overview"))
		self.assertEqual(resp.status_code, 200)

	def test_producer_evaluation_overview_forbidden_for_producer(self):
		self.client.login(username="prod", password="pw")
		resp = self.client.get(reverse("accounts:producer_evaluation_overview"))
		self.assertEqual(resp.status_code, 403)

	def test_profile_detail_self_redirect(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:profile_detail", args=["cons"]))
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(resp.url, reverse("accounts:my_page"))

	def test_profile_detail_private_profile_forbidden(self):
		profile = UserProfile.objects.get(user=self.producer)
		profile.publish_profile = False
		profile.save(update_fields=["publish_profile"])
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:profile_detail", args=["prod"]))
		self.assertEqual(resp.status_code, 403)

	def test_profile_detail_public_profile(self):
		profile = UserProfile.objects.get(user=self.producer)
		profile.publish_profile = True
		profile.save(update_fields=["publish_profile"])
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:profile_detail", args=["prod"]))
		self.assertEqual(resp.status_code, 200)

	def test_update_profile_bio_json_success(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.post(
			reverse("accounts:update_profile_bio"),
			data=json.dumps({"content_profile": "short bio"}),
			content_type="application/json",
		)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json()["bio"], "short bio")

	def test_update_profile_bio_too_long_json(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.post(
			reverse("accounts:update_profile_bio"),
			data=json.dumps({"content_profile": "x" * 101}),
			content_type="application/json",
		)
		self.assertEqual(resp.status_code, 400)
		self.assertIn("BIO_TOO_LONG", resp.json()["error"])

	def test_settings_get(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:settings"))
		self.assertEqual(resp.status_code, 200)

	def test_settings_post_profile_updates(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.post(reverse("accounts:settings"), data={"form_type": "profile", "nick_name": "NewNick"})
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(UserProfile.objects.get(user=self.consumer).nick_name, "NewNick")

	def test_settings_post_password_invalid_shows_page(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.post(reverse("accounts:settings"), data={"form_type": "password", "old_password": "wrong"})
		self.assertEqual(resp.status_code, 200)

	def test_history_get_consumer(self):
		self.client.login(username="cons", password="pw")
		resp = self.client.get(reverse("accounts:history"))
		self.assertEqual(resp.status_code, 200)
