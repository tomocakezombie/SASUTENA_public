from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

# from login import get_user_model
from django.contrib.auth import get_user_model
from .models import ExpirationNoticeSetting
from .forms import TagTypeForm, ExpirationNoticeSettingForm
from product.models import TagType


class AdminPortalTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_user(username="adminuser", password="pass", role="admin")
		self.user = User.objects.create_user(username="normaluser", password="pass", role="producer")

	def test_expiration_notice_str(self):
		notice = ExpirationNoticeSetting.objects.create(notify_days_before=5, is_active=True)
		s = str(notice)
		self.assertIn("通知設定", s)

	def test_tagtypeform_duplicate_name(self):
		TagType.objects.create(tag_name="有機")
		form = TagTypeForm(data={"tag_name": " 有機 "})
		self.assertFalse(form.is_valid())
		self.assertIn("同じ名前のタグが既に存在します。", form.errors.get("tag_name", []))

	def test_manage_tags_view_requires_admin(self):
		# non-admin user should be redirected
		self.client.login(username="normaluser", password="pass")
		url = reverse("adminPortal:manage_tags")
		resp = self.client.get(url)
		self.assertNotEqual(resp.status_code, 200)


class AdminPortalFormAndModelTests(TestCase):
	def setUp(self):
		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.admin = User.objects.create_user(username="ad2", password="pw", role="admin")

	def test_tag_name_length_boundaries(self):
		# TagType max length is 31
		from product.models import TagType
		ok_minus = "a" * 30
		ok_exact = "a" * 31
		nok_plus = "a" * 32
		t = TagType.objects.create(tag_name=ok_exact)
		self.assertEqual(len(str(t)), 31)
		form_ok = TagTypeForm(data={"tag_name": ok_minus})
		self.assertTrue(form_ok.is_valid())
		form_exact = TagTypeForm(data={"tag_name": ok_exact})
		self.assertFalse(form_exact.is_valid())
		# existing unique name will be caught by TagTypeForm.clean_tag_name
		form_dup = TagTypeForm(data={"tag_name": ok_exact})
		self.assertFalse(form_dup.is_valid())

	def test_expiration_notice_form_save(self):
		form = ExpirationNoticeSettingForm(data={
			"message": "m",
			"bg_color": "#ffffff",
			"text_color": "#000000",
			"is_active": True,
			"notify_days_before": 3,
		})
		self.assertTrue(form.is_valid())
		inst = form.save()
		self.assertIsNotNone(inst.pk)
