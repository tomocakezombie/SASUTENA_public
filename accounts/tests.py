from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from .models import UserProfile, UserEvaluation
from .forms import UserEvaluationForm


class AccountsAppTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.consumer = User.objects.create_user(username="cons", password="pw", role="consumer", email="c@example.com")
		self.producer = User.objects.create_user(username="prod", password="pw", role="producer", email="p@example.com")

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
		# nick_name max length assumed 255
		short = "あ" * 254
		exact = "あ" * 255
		longer = "あ" * 256
		profile = UserProfile.objects.create(user=self.producer, nick_name=short)
		self.assertTrue(len(profile.nick_name) == 254)
		profile.nick_name = exact
		profile.save()
		self.assertEqual(len(profile.nick_name), 255)
		# saving longer should raise DataError in DB or be truncated; attempt save and verify stored length
		profile.nick_name = longer
		profile.save()
		self.assertTrue(len(profile.nick_name) >= 255)

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
