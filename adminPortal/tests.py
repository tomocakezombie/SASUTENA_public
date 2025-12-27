from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import ExpirationNoticeSetting
from .forms import TagTypeForm
from product.models import TagType


class AdminPortalTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_user(username="adminuser", password="pass", role="admin")
		self.user = User.objects.create_user(username="normaluser", password="pass", role="producer")

	def test_manage_tags_url(self):
		"""
		# テスト関数名: test_manage_tags_url
		# 対象URL: adminPortal:manage_tags
		# テスト観点: URLの逆引き確認
		# 入力値: なし
		# 期待結果: 正しいURLが生成される
		"""
		url = reverse("adminPortal:manage_tags")
		self.assertEqual(url, "/adminPortal/manage_tags/")

	def test_manage_tags_view_requires_admin(self):
		"""
		# テスト関数名: test_manage_tags_view_requires_admin
		# 対象URL: adminPortal:manage_tags
		# テスト観点: 権限確認
		# 入力値: ログインユーザー（producer）
		# 期待結果: 403 Forbidden
		"""
		self.client.login(username="normaluser", password="pass")
		url = reverse("adminPortal:manage_tags")
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 403)

	def test_expiration_notice_str(self):
		notice = ExpirationNoticeSetting.objects.create(notify_days_before=5, is_active=True)
		s = str(notice)
		self.assertIn("通知設定", s)

	def test_tagtypeform_duplicate_name(self):
		"""
		# テスト関数名: test_tagtypeform_duplicate_name
		# 対象URL: なし（フォームテスト）
		# テスト観点: 同値テスト（重複チェック）
		# 入力値: tag_name="有機"
		# 期待結果: フォームが無効になる
		"""
		TagType.objects.create(tag_name="有機")
		form = TagTypeForm(data={"tag_name": " 有機 "})
		self.assertFalse(form.is_valid())
		self.assertIn("同じ名前のタグが既に存在します。", form.errors.get("tag_name", []))

	def test_tag_name_length_boundaries(self):
		"""
		# テスト関数名: test_tag_name_length_boundaries
		# 対象URL: なし（モデルテスト）
		# テスト観点: 境界値テスト
		# 入力値: 最大長31文字、最小長1文字
		# 期待結果: モデルが正しく保存される
		"""
		ok_exact = "a" * 31
		nok_plus = "a" * 32
		TagType.objects.create(tag_name=ok_exact)  # 正常系
		with self.assertRaises(Exception):
			TagType.objects.create(tag_name=nok_plus)  # 異常系

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
