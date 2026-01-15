from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Product, TagType
from .forms import ProductForm
from adminPortal.models import ExpirationNoticeSetting


class ProductAppTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.producer = User.objects.create_user(username="prod", password="pw", role="producer")

    def test_product_str(self):
        """
        # テスト関数名: test_product_str
        # 対象URL: なし（モデルテスト）
        # テスト観点: __str__ メソッドの動作確認
        # 入力値: 商品名 "トマト"
        # 期待結果: __str__ の戻り値に商品名が含まれる
        """
        p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
        self.assertIn("トマト", str(p))

    def test_productform_end_before_start_invalid(self):
        """
        # テスト関数名: test_productform_end_before_start_invalid
        # 対象URL: なし（フォームテスト）
        # テスト観点: 終了日が開始日より前の場合の検証
        # 入力値: 開始日 > 終了日
        # 期待結果: フォームが無効になる
        """
        start = (timezone.now() + timedelta(days=2)).date()
        end = (timezone.now() + timedelta(days=1)).date()
        data = {
            "item_name": "x",
            "number": 1,
            "description": "d",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "start_clock": "00:00",
            "end_clock": "00:00",
        }
        form = ProductForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)

    def test_productform_rejects_inactive_tag(self):
        inactive = TagType.objects.create(tag_name="無効タグ", is_active=False)
        start = timezone.now().date()
        data = {
            "item_name": "x",
            "number": 1,
            "description": "d",
            "start_date": start.isoformat(),
            "end_date": start.isoformat(),
            "start_clock": "00:00",
            "end_clock": "00:00",
            "tag_input": inactive.tag_name,
        }
        form = ProductForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("tag_input", form.errors)

    def test_productform_accepts_active_tag(self):
        TagType.objects.create(tag_name="有効タグ", is_active=True)
        start = timezone.now().date()
        data = {
            "item_name": "x",
            "number": 1,
            "description": "d",
            "start_date": start.isoformat(),
            "end_date": start.isoformat(),
            "start_clock": "00:00",
            "end_clock": "00:00",
            "tag_input": "有効タグ",
        }
        form = ProductForm(data=data)
        self.assertTrue(form.is_valid())

    def test_get_expiring_products_respects_settings(self):
        """
        # テスト関数名: test_get_expiring_products_respects_settings
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: 有効期限通知設定の尊重
        # 入力値: notify_days_before=2 の設定
        # 期待結果: 通知対象の商品が正しく取得される
        """
        notice = ExpirationNoticeSetting.objects.create(is_active=True, notify_days_before=2)
        now = timezone.now()
        p = Product.objects.create(item_name="soon", number=1, start_time=now, end_time=now + timedelta(days=1), description="d", user=self.producer, publish=True, valid=True, show_expiration_notice=True, completed=False)
        from .views import get_expiring_products
        qs = get_expiring_products()
        self.assertIn(p, list(qs))

    def test_product_create_url(self):
        """
        # テスト関数名: test_product_create_url
        # 対象URL: /product/create/
        # テスト観点: 商品作成ページのURLが正しく設定されているか
        # 入力値: なし
        # 期待結果: ステータスコード 200（成功）
        """
        url = reverse('product:create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_detail_url(self):
        """
        # テスト関数名: test_product_detail_url
        # 対象URL: /product/<id>/
        # テスト観点: 商品詳細ページのURLが正しく設定されているか
        # 入力値: 既存の商品ID
        # 期待結果: ステータスコード 200（成功）
        """
        p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
        url = reverse('product:detail', args=[p.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_update_url(self):
        """
        # テスト関数名: test_product_update_url
        # 対象URL: /product/update/<id>/
        # テスト観点: 商品更新ページのURLが正しく設定されているか
        # 入力値: 既存の商品ID
        # 期待結果: ステータスコード 200（成功）
        """
        p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
        url = reverse('product:update', args=[p.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_delete_url(self):
        """
        # テスト関数名: test_product_delete_url
        # 対象URL: /product/delete/<id>/
        # テスト観点: 商品削除ページのURLが正しく設定されているか
        # 入力値: 既存の商品ID
        # 期待結果: ステータスコード 200（成功）
        """
        p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
        url = reverse('product:delete', args=[p.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_product_create_boundary(self):
        """
        # テスト関数名: test_product_create_boundary
        # 対象URL: /product/create/
        # テスト観点: 商品作成時の境界値テスト
        # 入力値: 商品名の最大長, 最小数, 最大数
        # 期待結果: ステータスコード 302（リダイレクト）、商品が正しく作成される
        """
        url = reverse('product:create')
        data = {
            "item_name": "a" * 255,  # 商品名の最大長
            "number": 1,
            "description": "d",
            "start_date": (timezone.now()).date().isoformat(),
            "end_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            "start_clock": "00:00",
            "end_clock": "00:00",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(item_name="a" * 255).exists())

    def test_product_update_boundary(self):
        """
        # テスト関数名: test_product_update_boundary
        # 対象URL: /product/update/<id>/
        # テスト観点: 商品更新時の境界値テスト
        # 入力値: 商品名の最大長, 最小数, 最大数
        # 期待結果: ステータスコード 302（リダイレクト）、商品情報が正しく更新される
        """
        p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
        url = reverse('product:update', args=[p.id])
        data = {
            "item_name": "いちご" * 20,  # 商品名の最大長
            "number": 999,
            "description": "d",
            "start_date": (timezone.now()).date().isoformat(),
            "end_date": (timezone.now() + timedelta(days=1)).date().isoformat(),
            "start_clock": "00:00",
            "end_clock": "00:00",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.item_name, "いちご" * 20)
        self.assertEqual(p.number, 999)
