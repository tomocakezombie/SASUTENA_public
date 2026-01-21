from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import ExpirationNoticeSetting
from .forms import TagTypeForm
from product.models import TagType
from .forms import ExpirationNoticeSettingForm
from django.core.exceptions import ValidationError

from product.models import Product
from login.models import AccountRequest



class AdminPortalView1Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="adminuser", password="pass", role="admin"
        )
        self.user = User.objects.create_user(
            username="normaluser", password="pass", role="producer"
        )

    def test_admin_portal_list_url(self):
        """
        # テスト関数名: test_admin_portal_list_url
        # 対象URL: adminPortal:admin_portal_list
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:admin_portal_list")
        self.assertEqual(url, "/admin-portal/")

    def test_admin_my_page_url(self):
        """
        # テスト関数名: test_admin_my_page_url
        # 対象URL: adminPortal:my_page
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:my_page")
        self.assertEqual(url, "/admin-portal/my-page/")

    def test_admin_message_monitor_url(self):
        """
        # テスト関数名: test_admin_message_monitor_url
        # 対象URL: adminPortal:admin_message_monitor
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:admin_message_monitor")
        self.assertEqual(url, "/admin-portal/messages/")

    def test_admin_product_detail_url(self):
        """
        # テスト関数名: test_admin_product_detail_url
        # 対象URL: adminPortal:admin_product_detail
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:admin_product_detail", args=[1])
        self.assertEqual(url, "/admin-portal/products/1/")

    def test_approve_account_request_url(self):
        """
        # テスト関数名: test_approve_account_request_url
        # 対象URL: adminPortal:approve_account_request
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:approve_account_request", args=[1])
        self.assertEqual(url, "/admin-portal/requests/1/approve/")

    def test_reject_product_url(self):
        """
        # テスト関数名: test_reject_product_url
        # 対象URL: adminPortal:reject_product
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:reject_product", args=[1])
        self.assertEqual(url, "/admin-portal/products/1/reject/")

    def test_toggle_product_visibility_url(self):
        """
        # テスト関数名: test_toggle_product_visibility_url
        # 対象URL: adminPortal:toggle_product_visibility
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:toggle_product_visibility", args=[1])
        self.assertEqual(url, "/admin-portal/products/1/toggle/")

    def test_manage_tags_url(self):
        """
        # テスト関数名: test_manage_tags_url
        # 対象URL: adminPortal:manage_tags
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:manage_tags")
        self.assertEqual(url, "/admin-portal/tags/")

    def test_toggle_tag_status_url(self):
        """
        # テスト関数名: test_toggle_tag_status_url
        # 対象URL: adminPortal:toggle_tag_status
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:toggle_tag_status", args=[1])
        self.assertEqual(url, "/admin-portal/tags/1/toggle-status/")

    def test_manage_expiration_notice_url(self):
        """
        # テスト関数名: test_manage_expiration_notice_url
        # 対象URL: adminPortal:manage_expiration_notice
        # テスト観点: URLの逆引き確認
        # 入力値: なし
        # 期待結果: 正しいURLが生成される
        """
        url = reverse("adminPortal:manage_expiration_notice")
        self.assertEqual(url, "/admin-portal/expiration_notice/")


class AdminPortalView2Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="adminuser", password="pass", role="admin"
        )
        self.user = User.objects.create_user(
            username="normaluser", password="pass", role="producer"
        )
        self.product = Product.objects.create(
            item_name="Test Item",
            number=1,
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(days=1),
            description="Test Description",
            user=self.user,
        )

    def test_approve_account_request(self):
        self.client.login(username="adminuser", password="pass")

        req = AccountRequest.objects.create(
			username="newuser",
			email="test@example.com",
			is_verified=False,
			is_approved=False,
		)
        
        url = reverse("adminPortal:approve_account_request", args=[req.pk])
        url = reverse("adminPortal:approve_account_request", args=[req.pk])
        resp = self.client.post(url)

        self.assertEqual(resp.status_code, 302)
        req.refresh_from_db()
        self.assertTrue(req.is_approved)


    def test_toggle_product_visibility_unpublish(self):
        self.client.login(username="adminuser", password="pass")
        self.product.valid = True
        self.product.publish = True
        self.product.save()

        url = reverse("adminPortal:toggle_product_visibility", args=[self.product.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        self.product.refresh_from_db()
        self.assertFalse(self.product.publish)

    def test_toggle_tag_status_deactivate(self):
        self.client.login(username="adminuser", password="pass")
        tag = TagType.objects.create(tag_name="有機野菜")

        url = reverse("adminPortal:toggle_tag_status", args=[tag.pk])
        resp = self.client.post(url, {"is_active": "0"})

        self.assertEqual(resp.status_code, 302)
        tag.refresh_from_db()
        self.assertFalse(tag.is_active)

    def test_toggle_tag_status_reactivate(self):
        self.client.login(username="adminuser", password="pass")
        tag = TagType.objects.create(tag_name="特別栽培", is_active=False)

        url = reverse("adminPortal:toggle_tag_status", args=[tag.pk])
        resp = self.client.post(url, {"is_active": "1"})

        self.assertEqual(resp.status_code, 302)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)

    def test_manage_tags_default_sort_by_id(self):
        self.client.login(username="adminuser", password="pass")
        first = TagType.objects.create(tag_name="Bタグ")
        second = TagType.objects.create(tag_name="Aタグ")

        url = reverse("adminPortal:manage_tags")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        tags = list(resp.context["tag_list"])
        self.assertEqual([t.pk for t in tags[:2]], [first.pk, second.pk])
        self.assertEqual(resp.context["sort_field"], "id")
        self.assertEqual(resp.context["sort_dir"], "asc")

    def test_toggle_tag_status_requires_admin(self):
        self.client.login(username="normaluser", password="pass")
        tag = TagType.objects.create(tag_name="減農薬")

        url = reverse("adminPortal:toggle_tag_status", args=[tag.pk])
        resp = self.client.post(url, {"is_active": "0"})

        self.assertEqual(resp.status_code, 302)
        tag.refresh_from_db()
        self.assertTrue(tag.is_active)

    def test_delete_tag_removes_record(self):
        self.client.login(username="adminuser", password="pass")
        tag = TagType.objects.create(tag_name="削除用")

        url = reverse("adminPortal:delete_tag", args=[tag.pk])
        resp = self.client.post(url)

        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TagType.objects.filter(pk=tag.pk).exists())

    def test_delete_tag_requires_admin(self):
        self.client.login(username="normaluser", password="pass")
        tag = TagType.objects.create(tag_name="削除失敗")

        url = reverse("adminPortal:delete_tag", args=[tag.pk])
        resp = self.client.post(url)

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TagType.objects.filter(pk=tag.pk).exists())

    def test_manage_tags_search_filters_results(self):
        self.client.login(username="adminuser", password="pass")
        matched = TagType.objects.create(tag_name="有機野菜セット")
        TagType.objects.create(tag_name="減農薬りんご")

        url = reverse("adminPortal:manage_tags")
        resp = self.client.get(url, {"q": "有機"})

        self.assertEqual(resp.status_code, 200)
        tags = list(resp.context["tag_list"])
        self.assertIn(matched, tags)
        self.assertEqual(len(tags), 1)
        self.assertEqual(resp.context["search_query"], "有機")

    def test_reject_product_with_reason(self):
        self.client.login(username="adminuser", password="pass")
        url = reverse("adminPortal:reject_product", args=[self.product.pk])
        resp = self.client.post(url, {"reason": "品質に問題あり"})
        self.assertEqual(resp.status_code, 302)

        self.product.refresh_from_db()
        self.assertFalse(self.product.valid)
        self.assertFalse(self.product.publish)
        self.assertEqual(self.product.admin_comment, "品質に問題あり")

    def test_reject_product_without_reason(self):
        self.client.login(username="adminuser", password="pass")

        self.product.valid = True
        self.product.publish = True
        self.product.save()
        url = reverse("adminPortal:reject_product", args=[self.product.pk])
        url = reverse("adminPortal:reject_product", args=[self.product.pk])
        resp = self.client.post(url, {"reason": ""})

        self.assertEqual(resp.status_code, 302)

        self.product.refresh_from_db()
        self.assertTrue(self.product.valid)
        self.assertTrue(self.product.publish)
    def test_undo_reject_product(self):
        self.client.login(username="adminuser", password="pass")
        self.product.valid = False
        self.product.rejected_at = timezone.now()
        self.product.admin_comment = "不備あり"
        self.product.save()

        url = reverse("adminPortal:reject_product", args=[self.product.pk])
        resp = self.client.post(url, {"mode": "undo"})
        self.assertEqual(resp.status_code, 302)

        self.product.refresh_from_db()
        self.assertTrue(self.product.valid)
        self.assertIsNone(self.product.rejected_at)
        self.assertEqual(self.product.admin_comment, "")

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
        # 対象URL: TagTypeモデル
        # テスト観点: 境界値テスト
        # 入力値: 最大長31文字、最小長1文字
        # 期待結果: モデルが正しく保存される
        """
        ok = TagType(tag_name="a" * 31)
        ok.full_clean()

        ng = TagType(tag_name="a" * 32)
        with self.assertRaises(ValidationError):
            ng.full_clean()
    def test_expiration_notice_setting_form_valid_and_save(self):
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

    def test_expiration_notice_setting_form_invalid_zero(self):
        form = ExpirationNoticeSettingForm(data={
            "message": "test",
            "bg_color": "#ffffff",
            "text_color": "#000000",
            "is_active": True,
            "notify_days_before": 0,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("notify_days_before", form.errors)

    def test_expiration_notice_setting_form_invalid_negative(self):
        form = ExpirationNoticeSettingForm(data={
            "message": "test",
            "bg_color": "#ffffff",
            "text_color": "#000000",
            "is_active": True,
            "notify_days_before": -1,
        })
        self.assertFalse(form.is_valid())

    def test_tagtypeform_empty_name(self):
        form = TagTypeForm(data={"tag_name": " "})
        self.assertFalse(form.is_valid())

    def test_tagtypeform_too_long(self):
        form = TagTypeForm(data={"tag_name": "a" * 32})
        self.assertFalse(form.is_valid())