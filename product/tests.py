from datetime import date, timedelta, time as dt_time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Product, TagType
from .forms import ProductForm
from adminPortal.models import ExpirationNoticeSetting
from product.forms import ProductForm, ProductApplicationForm, ProductCommentForm
from product.mentions import extract_mentions, sync_comment_mentions
from product.models import (
    Product,
    ProductApplication,
    ProductComment,
    ProductCommentMention,
        ProductTag,
        TagType,
)
from product.views import get_expiring_products


class ProductAppModelsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.producer = User.objects.create_user(
            username="producer-models",
            password="pw",
            role="producer",
        )
        self.consumer = User.objects.create_user(
            username="consumer-models",
            password="pw",
            role="consumer",
        )
        now = timezone.now()
        self.product = Product.objects.create(
            item_name="Sample",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="desc",
            user=self.producer,
            publish=True,
            valid=True,
        )

    def test_product_str_includes_item_name(self):
        """__str__ が商品名を含むか確認して表示名の退行を防ぐ。"""
        self.assertIn("Sample", str(self.product))

    def test_product_application_str_contains_keyword(self):
        """申込モデルの __str__ にキーワード Application が含まれることを確認。"""
        application = ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            quantity=1,
            message="msg",
        )
        self.assertIn("Application", str(application))

    def test_product_default_flags_are_false(self):
        """公開・承認・完了・締切通知フラグの初期値が False であることを検証。"""
        product = Product.objects.create(
            item_name="Defaults",
            number=5,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=3),
            description="desc",
            user=self.producer,
        )
        self.assertFalse(product.publish)
        self.assertFalse(product.valid)
        self.assertFalse(product.completed)
        self.assertFalse(product.show_expiration_notice)

    def test_productapplication_default_status_pending(self):
        """申込作成時の既定ステータスが STATUS_PENDING になるか確認。"""
        application = ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            quantity=2,
            message="pending",
        )
        self.assertEqual(application.apply_status, ProductApplication.STATUS_PENDING)

    def test_productcomment_str_contains_username(self):
        """コメントの __str__ に投稿者と商品名が現れるかを確認。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="hello",
        )
        self.assertIn(self.consumer.username, str(comment))
        self.assertIn(self.product.item_name, str(comment))

    def test_productcomment_default_flags_false(self):
        """コメントの削除・編集フラグ初期値が False かを検証。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="check",
        )
        self.assertFalse(comment.delete_flag)
        self.assertFalse(comment.edit_flag)

    def test_productcommentmention_unique_constraint_prevents_duplicates(self):
        """同一コメントで同じユーザーを二重にメンションできない制約を確認。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="@" + self.producer.username,
        )
        mention = ProductCommentMention.objects.create(
            comment=comment,
            mentioned_user=self.producer,
        )
        self.assertEqual(str(mention), f"{mention.comment_id} -> {self.producer}")
        with self.assertRaises(IntegrityError):
            ProductCommentMention.objects.create(
                comment=comment,
                mentioned_user=self.producer,
            )

    def test_product_published_at_accepts_timestamp(self):
        """published_at に日時を設定すると保持されることを確認。"""
        product = Product.objects.create(
            item_name="Publish",
            number=2,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1),
            description="desc",
            user=self.producer,
        )
        published_time = timezone.now()
        product.published_at = published_time
        product.save(update_fields=["published_at"])
        product.refresh_from_db()
        self.assertEqual(product.published_at, published_time)

    def test_productapplication_quantity_default_decimal(self):
        """quantity のデフォルトが Decimal('1') になることを確認。"""
        application = ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            message="default-qty",
        )
        self.assertEqual(application.quantity, Decimal("1"))

    def test_productapplication_status_transition(self):
        """申請ステータスを APPROVED に更新できることを検証。"""
        application = ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            quantity=1,
            message="approve",
        )
        application.apply_status = ProductApplication.STATUS_APPROVED
        application.save(update_fields=["apply_status"])
        application.refresh_from_db()
        self.assertEqual(application.apply_status, ProductApplication.STATUS_APPROVED)

    def test_productcomment_ordering_is_descending(self):
        """コメントが comment_time 降順で返される ordering を確認。"""
        older = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="old",
        )
        newer = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="new",
        )
        comments = list(self.product.comments.all())
        self.assertEqual(comments[0], newer)
        self.assertEqual(comments[1], older)


class ProductAppProductFormTests(TestCase):
    def test_form_valid_when_end_after_start(self):
        today = date.today()
        form = ProductForm(
            data={
                "item_name": "F1",
                "number": 1,
                "description": "d",
                "start_date": today.isoformat(),
                "start_clock": "00:00",
                "end_date": today.isoformat(),
                "end_clock": "23:59",
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid_when_end_before_start(self):
        today = date.today()
        form = ProductForm(
            data={
                "item_name": "F1",
                "number": 1,
                "description": "d",
                "start_date": today.isoformat(),
                "start_clock": "12:00",
                "end_date": today.isoformat(),
                "end_clock": "00:00",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)

    def test_form_defaults_missing_times(self):
        """開始・終了時間未入力でも既定値が補われる。"""
        today = date.today()
        form = ProductForm(
            data={
                "item_name": "DefaultTime",
                "number": 1,
                "description": "d",
                "start_date": today.isoformat(),
                "start_clock": "",
                "end_date": today.isoformat(),
                "end_clock": "",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["start_clock"], dt_time(0, 0))
        self.assertEqual(form.cleaned_data["end_clock"], dt_time(23, 59))
        self.assertEqual(form.cleaned_data["start_time"].date(), today)
        self.assertEqual(form.cleaned_data["end_time"].date(), today)
        self.assertEqual(form.cleaned_data["start_time"].time(), dt_time(0, 0))
        self.assertEqual(form.cleaned_data["end_time"].time(), dt_time(23, 59))

    def test_form_save_combines_date_and_time(self):
        """save(commit=False) で start_time/end_time が結合される。"""
        today = date.today()
        form = ProductForm(
            data={
                "item_name": "Combined",
                "number": 3,
                "description": "desc",
                "start_date": today.isoformat(),
                "start_clock": "09:30",
                "end_date": (today + timedelta(days=1)).isoformat(),
                "end_clock": "14:15",
            }
        )
        self.assertTrue(form.is_valid())
        product = form.save(commit=False)
        self.assertEqual(product.start_time.date(), today)
        self.assertEqual(product.end_time.date(), today + timedelta(days=1))
        self.assertEqual(product.start_time.time(), dt_time(9, 30))
        self.assertEqual(product.end_time.time(), dt_time(14, 15))

    def test_form_initializes_tags_for_instance(self):
        """既存商品のタグが初期値として設定される。"""
        user_model = get_user_model()
        user = user_model.objects.create_user(username="form-tag", password="pw", role="producer")
        now = timezone.now()
        product = Product.objects.create(
            item_name="Tagged",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="d",
            user=user,
        )
        tag_active = TagType.objects.create(tag_name="Active")
        product.tags.add(tag_active)
        form = ProductForm(instance=product)
        initial = list(form.fields["tags"].initial)
        self.assertEqual(initial, [tag_active.pk])

    def test_form_tags_queryset_sorted(self):
        """タグ候補が名前順でソートされる。"""
        TagType.objects.create(tag_name="Banana")
        TagType.objects.create(tag_name="Apple")
        form = ProductForm()
        tag_names = list(form.fields["tags"].queryset.values_list("tag_name", flat=True))
        self.assertEqual(tag_names, ["Apple", "Banana"])


class ProductAppApplicationFormTests(TestCase):
    def test_message_required(self):
        """メッセージ未入力でバリデーションエラーとなることを確認。"""
        form = ProductApplicationForm(data={"message": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_message_valid(self):
        """メッセージ入力済みならフォームが有効になる。"""
        form = ProductApplicationForm(data={"message": "希望日時をご相談ください"})
        self.assertTrue(form.is_valid())


class ProductAppCommentFormTests(TestCase):
    def test_comment_required(self):
        """コメント未入力のときエラーが返るかを検証。"""
        form = ProductCommentForm(data={"content": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_comment_max_length(self):
        """最大長511文字は許容し512文字はエラーになるか確認。"""
        form = ProductCommentForm(data={"content": "a" * 511})
        self.assertTrue(form.is_valid())
        too_long = ProductCommentForm(data={"content": "a" * 512})
        self.assertFalse(too_long.is_valid())
        self.assertIn("content", too_long.errors)


class ProductAppTagModelsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.producer = User.objects.create_user(username="tag-producer", password="pw", role="producer")
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
        self.product = Product.objects.create(
            item_name="Tagged",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="desc",
            user=self.producer,
        )
        self.tag = TagType.objects.create(tag_name="Leafy")

    def test_tagtype_str_returns_name(self):
        """TagType の __str__ がタグ名を返すか確認。"""
        self.assertEqual(str(self.tag), "Leafy")

    def test_producttag_str_and_relationship(self):
        """ProductTag を介した多対多関連の生成と __str__ を検証。"""
        mapping = ProductTag.objects.create(product=self.product, tag=self.tag)
        self.assertEqual(str(mapping), f"{self.product} -> {self.tag}")
        linked_tags = list(self.product.tags.all())
        self.assertEqual(linked_tags, [self.tag])

    def test_producttag_unique_constraint(self):
        """同じ product/tag 組は unique_together により二重登録できない。"""
        ProductTag.objects.create(product=self.product, tag=self.tag)
        with self.assertRaises(IntegrityError):
            ProductTag.objects.create(product=self.product, tag=self.tag)


class ProductAppURLsTests(SimpleTestCase):
    def test_basic_product_urls(self):
        self.assertEqual(reverse("product:product_create"), "/product/create/")
        self.assertEqual(reverse("product:product_list"), "/product/list/")
        self.assertEqual(reverse("product:consumer_product_list"), "/product/consumer/list/")
        self.assertEqual(reverse("product:producer_product_list"), "/product/producer/list/")

    def test_product_urls_requiring_identifiers(self):
        self.assertEqual(reverse("product:product_detail", args=[5]), "/product/5/")
        self.assertEqual(reverse("product:product_delete", args=[5]), "/product/delete/5/")
        self.assertEqual(reverse("product:product_complete", args=[5]), "/product/producer/5/complete/")
        self.assertEqual(
            reverse("product:toggle_expiration_notice", args=[5]),
            "/product/product/5/toggle_notice/",
        )
        self.assertEqual(
            reverse("product:comment_update", args=[7]),
            "/product/comment/7/update/",
        )
        self.assertEqual(
            reverse("product:comment_delete", args=[7]),
            "/product/comment/7/delete/",
        )



class BaseProductViewTestCase(TestCase):
    """商品アプリのビュー検証で共通となる初期データを生成する基底クラス。"""

    def setUp(self):
        User = get_user_model()
        self.producer = User.objects.create_user(
            username="producer-views",
            password="pw",
            role="producer",
        )
        self.consumer = User.objects.create_user(
            username="consumer-views",
            password="pw",
            role="consumer",
        )
        now = timezone.now()
        self.product = Product.objects.create(
            item_name="ViewTarget",
            number=2,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="desc",
            user=self.producer,
            publish=True,
            valid=True,
        )
        self.comment = ProductComment.objects.create(
            product=self.product,
            user=self.consumer,
            content="元のコメント",
        )


class ProductCreateViewTests(BaseProductViewTestCase):
    def test_producer_can_access_create_view(self):
        """生産者権限で商品作成画面を開けるか確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.get(reverse("product:product_create"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login_for_create(self):
        """未ログインユーザーは next 付きでログイン画面へ飛ばされるか検証。"""
        response = self.client.get(reverse("product:product_create"))
        expected_url = f"{reverse('login:index')}?next={reverse('product:product_create')}"
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_consumer_redirected_from_producer_only_create(self):
        """消費者が生産者専用ページに来た場合のリダイレクト先を確認。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.get(reverse("product:product_create"))
        self.assertRedirects(response, reverse("product:consumer_product_list"))


class ProductListViewTests(BaseProductViewTestCase):
    def test_product_list_redirects_to_producer_dashboard(self):
        """product_list が生産者ダッシュボードへリダイレクトするか確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.get(reverse("product:product_list"))
        self.assertRedirects(response, reverse("product:producer_product_list"))


class ConsumerProductListViewTests(BaseProductViewTestCase):
    def test_consumer_product_list_access(self):
        """消費者が消費者向け一覧にアクセスできるか検証。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.get(reverse("product:consumer_product_list"))
        self.assertEqual(response.status_code, 200)

    def test_producer_redirected_from_consumer_list(self):
        """生産者が消費者ページに来た際のリダイレクトを確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.get(reverse("product:consumer_product_list"))
        self.assertEqual(response.status_code, 302)


class ProducerProductListViewTests(BaseProductViewTestCase):
    def test_producer_product_list_returns_expected_context(self):
        """生産者ダッシュボードが 200 を返し自分の商品を文脈に含むか確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.get(reverse("product:producer_product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.product, response.context["my_products"])

    def test_consumer_redirected_from_producer_dashboard(self):
        """消費者が生産者ダッシュボードを開こうとすると自分の一覧へ飛ぶか検証。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.get(reverse("product:producer_product_list"))
        self.assertRedirects(response, reverse("product:consumer_product_list"))


class ProductDetailViewTests(BaseProductViewTestCase):
    def test_product_detail_accessible_to_consumer(self):
        """消費者が公開商品の詳細を閲覧できることを確かめる。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.get(reverse("product:product_detail", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)

    def test_consumer_denied_non_public_detail(self):
        """非公開または未承認商品を消費者が開くと一覧へ戻るか確認。"""
        self.product.publish = False
        self.product.save(update_fields=["publish"])
        self.client.login(username="consumer-views", password="pw")
        response = self.client.get(reverse("product:product_detail", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:consumer_product_list"))


class ProductApplicationCancelViewTests(BaseProductViewTestCase):
    def setUp(self):
        super().setUp()
        self.application = ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            quantity=1,
            message="取り消しテスト",
        )

    def test_consumer_can_cancel_pending_application(self):
        """申込み者が保留中の申込みを取り消して一覧に戻れるか確認。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.post(
            reverse("product:application_cancel", args=[self.application.pk])
        )
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.assertFalse(ProductApplication.objects.filter(pk=self.application.pk).exists())

    def test_other_user_cannot_cancel_someone_application(self):
        """他ユーザーが申込みを取り消そうとしても拒否されることを確認。"""
        other_consumer = get_user_model().objects.create_user(
            username="other-consumer",
            password="pw",
            role="consumer",
        )
        self.client.login(username="other-consumer", password="pw")
        response = self.client.post(
            reverse("product:application_cancel", args=[self.application.pk])
        )
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.assertTrue(ProductApplication.objects.filter(pk=self.application.pk).exists())


class ProductDeleteViewTests(BaseProductViewTestCase):
    def test_producer_can_delete_own_product(self):
        """生産者が自分の商品を削除して一覧に戻るフローを検証。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:product_delete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_other_producer_cannot_delete_product(self):
        """別の生産者が他人の商品を削除できず元画面へ戻ることを確認。"""
        User = get_user_model()
        other = User.objects.create_user(
            username="other-producer-view",
            password="pw",
            role="producer",
        )
        self.client.login(username="other-producer-view", password="pw")
        response = self.client.post(reverse("product:product_delete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())


class ProductCompleteViewTests(BaseProductViewTestCase):
    def test_product_complete_marks_product_finished(self):
        """完了通知 POST 成功で完了フラグが立ち一覧へ戻るかを検証。"""
        ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            apply_status=ProductApplication.STATUS_APPROVED,
        )
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:product_complete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.product.refresh_from_db()
        self.assertTrue(self.product.completed)
        self.assertIsNotNone(self.product.completed_notified_at)

    def test_product_complete_allows_pending_application(self):
        """承認待ち申請が存在するだけで完了通知できることを確認。"""
        ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            apply_status=ProductApplication.STATUS_PENDING,
        )
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:product_complete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.product.refresh_from_db()
        self.assertTrue(self.product.completed)

    def test_product_complete_requires_existing_application(self):
        """申請が1件も無い場合は完了通知できないことを確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:product_complete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.product.refresh_from_db()
        self.assertFalse(self.product.completed)

    def test_product_complete_rejects_unapproved_product(self):
        """未承認商品の完了リクエストが却下されることを確認。"""
        ProductApplication.objects.create(
            product=self.product,
            user=self.consumer,
            apply_status=ProductApplication.STATUS_APPROVED,
        )
        self.product.valid = False
        self.product.save(update_fields=["valid"])
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:product_complete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:producer_product_list"))
        self.product.refresh_from_db()
        self.assertFalse(self.product.completed)


class ProductCommentUpdateViewTests(BaseProductViewTestCase):
    def test_comment_update_allows_owner_edit(self):
        """コメント投稿者が内容を更新して編集済みフラグが立つか検証。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.post(
            reverse("product:comment_update", args=[self.comment.pk]),
            {"content": "更新済みコメント"},
        )
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "更新済みコメント")
        self.assertTrue(self.comment.edit_flag)

    def test_comment_update_blocks_other_user(self):
        """他人のコメント更新が拒否され内容も変わらないことを確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(
            reverse("product:comment_update", args=[self.comment.pk]),
            {"content": "不正更新"},
        )
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "元のコメント")


class ProductCommentDeleteViewTests(BaseProductViewTestCase):
    def test_comment_delete_marks_flag_for_owner(self):
        """コメント投稿者が削除 POST すると削除フラグが立つか確かめる。"""
        self.client.login(username="consumer-views", password="pw")
        response = self.client.post(reverse("product:comment_delete", args=[self.comment.pk]))
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.delete_flag)

    def test_comment_delete_blocks_other_user(self):
        """他人のコメント削除が拒否され削除フラグが変わらないことを確認。"""
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:comment_delete", args=[self.comment.pk]))
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.delete_flag)


class ToggleExpirationNoticeViewTests(BaseProductViewTestCase):
    def test_toggle_expiration_notice_switches_flag(self):
        """通知トグル POST で show_expiration_notice が反転するか検証。"""
        self.product.show_expiration_notice = False
        self.product.save(update_fields=["show_expiration_notice"])
        self.client.login(username="producer-views", password="pw")
        response = self.client.post(reverse("product:toggle_expiration_notice", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:product_detail", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertTrue(self.product.show_expiration_notice)


class BaseProductUtilityTestCase(TestCase):
    """商品アプリの補助関数をテストするための共通セットアップ。"""

    def setUp(self):
        User = get_user_model()
        self.producer = User.objects.create_user(
            username="producer-views2",
            password="pw",
            role="producer",
        )
        self.author = User.objects.create_user(username="author-views2", password="pw")
        self.mentioned = User.objects.create_user(username="mention_target", password="pw")
        self.other = User.objects.create_user(username="other_user", password="pw")
        now = timezone.now()
        self.product = Product.objects.create(
            item_name="MentionTarget",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="desc",
            user=self.producer,
            publish=True,
            valid=True,
        )


class GetExpiringProductsTests(BaseProductUtilityTestCase):
    def test_get_expiring_products_respects_setting(self):
        """通知設定で指定日数以内の商品だけ抽出されるか確認。"""
        ExpirationNoticeSetting.objects.create(is_active=True, notify_days_before=2)
        now = timezone.now()
        target = Product.objects.create(
            item_name="Soon",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="desc",
            user=self.producer,
            publish=True,
            valid=True,
            show_expiration_notice=True,
        )
        late = Product.objects.create(
            item_name="Later",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=5),
            description="desc",
            user=self.producer,
            publish=True,
            valid=True,
            show_expiration_notice=True,
        )
        expiring = list(get_expiring_products())
        self.assertIn(target, expiring)
        self.assertNotIn(late, expiring)


class ExtractMentionsTests(BaseProductUtilityTestCase):
    def test_extract_mentions_returns_unique_usernames(self):
        """同じユーザー名のメンションが重複せず取得されるか検証。"""
        usernames = extract_mentions("Hello @mention_target and @mention_target again")
        self.assertEqual(usernames, {"mention_target"})


class SyncCommentMentionsTests(BaseProductUtilityTestCase):
    def test_sync_comment_mentions_creates_records(self):
        """既知ユーザーのメンションがレコード生成されるか確認。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @mention_target",
        )
        sync_comment_mentions(comment)
        mentions = ProductCommentMention.objects.filter(comment=comment)
        self.assertEqual(mentions.count(), 1)
        self.assertEqual(mentions.first().mentioned_user, self.mentioned)

    def test_sync_comment_mentions_ignores_unknown_users(self):
        """存在しないユーザー名のメンションが無視されるか検証。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @ghost",
        )
        sync_comment_mentions(comment)
        self.assertFalse(ProductCommentMention.objects.filter(comment=comment).exists())

    def test_sync_comment_mentions_updates_on_edit(self):
        """コメント編集時にメンション先が更新されるか確認。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @mention_target",
        )
        sync_comment_mentions(comment)
        comment.content = "Ping @other_user"
        comment.save(update_fields=["content"])
        sync_comment_mentions(comment)
        mention = ProductCommentMention.objects.get(comment=comment)
        self.assertEqual(mention.mentioned_user, self.other)

    def test_sync_comment_mentions_removes_when_no_mentions(self):
        """メンションを削除した際にレコードが消えるか検証。"""
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @mention_target",
        )
        sync_comment_mentions(comment)
        comment.content = "No mentions here"
        comment.save(update_fields=["content"])
        sync_comment_mentions(comment)
        self.assertFalse(ProductCommentMention.objects.filter(comment=comment).exists())
