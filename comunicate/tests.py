
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.shortcuts import resolve_url
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from . import views
from .forms import ConversationStartForm, MessageEditForm, MessageForm
from .models import Message
from product.models import Product


class ComunicateURLTests(SimpleTestCase):
	def test_url_patterns_reverse_and_resolve(self):
		cases = [
			(
				"comunicate:conversation_list",
				None,
				"/messages/",
				views.conversation_list,
				{},
			),
			(
				"comunicate:conversation_detail",
				{"username": "testuser"},
				"/messages/thread/testuser/",
				views.conversation_detail,
				{"username": "testuser"},
			),
			(
				"comunicate:conversation_detail_item",
				{"username": "testuser", "item_id": 1},
				"/messages/thread/testuser/item/1/",
				views.conversation_detail,
				{"username": "testuser", "item_id": 1},
			),
			(
				"comunicate:message_edit",
				{"pk": 1},
				"/messages/message/1/edit/",
				views.message_edit,
				{"pk": 1},
			),
			(
				"comunicate:message_delete",
				{"pk": 1},
				"/messages/message/1/delete/",
				views.message_delete,
				{"pk": 1},
			),
		]

		for name, kwargs, expected_path, expected_view, expected_kwargs in cases:
			with self.subTest(name=name):
				url = reverse(name, kwargs=kwargs) if kwargs else reverse(name)
				self.assertEqual(url, expected_path)

				match = resolve(expected_path)
				self.assertIs(match.func, expected_view)
				self.assertEqual(match.kwargs, expected_kwargs)


class MessageModelTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sender = user_model.objects.create_user(
			username="sender",
			email="sender@example.com",
			password="password123",
		)
		cls.receiver = user_model.objects.create_user(
			username="receiver",
			email="receiver@example.com",
			password="password123",
		)
		cls.product = Product.objects.create(
			item_name="Sample",
			number=1,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="Sample description",
			user=cls.sender,
		)

	def _create_message(self, **kwargs):
		defaults = {
			"send_user": self.sender,
			"receive_user": self.receiver,
			"message_content": "hello",
		}
		defaults.update(kwargs)
		return Message.objects.create(**defaults)

	def test_message_id_auto_assigned(self):
		message = self._create_message()
		self.assertIsNotNone(message.message_id)
		self.assertIsNotNone(message.send_time)

	def test_full_clean_requires_send_user(self):
		message = Message(
			receive_user=self.receiver,
			message_content="hello",
		)
		with self.assertRaises(ValidationError):
			message.full_clean()

	def test_full_clean_requires_receive_user(self):
		message = Message(
			send_user=self.sender,
			message_content="hello",
		)
		with self.assertRaises(ValidationError):
			message.full_clean()

	def test_message_content_length_validation(self):
		message = Message(
			send_user=self.sender,
			receive_user=self.receiver,
			message_content="",
		)
		with self.assertRaises(ValidationError):
			message.full_clean()

		valid_message = Message(
			send_user=self.sender,
			receive_user=self.receiver,
			message_content="a",
		)
		valid_message.full_clean()

		too_long = Message(
			send_user=self.sender,
			receive_user=self.receiver,
			message_content="a" * 512,
		)
		with self.assertRaises(ValidationError):
			too_long.full_clean()

	def test_mark_as_read_sets_flag(self):
		message = self._create_message()
		self.assertFalse(message.read_flag)
		message.mark_as_read()
		message.refresh_from_db()
		self.assertTrue(message.read_flag)

	def test_mark_as_deleted_sets_flag(self):
		message = self._create_message()
		self.assertFalse(message.delete_flag)
		message.mark_as_deleted()
		message.refresh_from_db()
		self.assertTrue(message.delete_flag)

	def test_item_allows_none(self):
		message = self._create_message(item=None)
		self.assertIsNone(message.item)

	def test_record_edit_updates_content_and_timestamp(self):
		message = self._create_message(item=self.product, message_content="before")
		original_updated_at = message.updated_at
		message.record_edit("after")
		message.refresh_from_db()
		self.assertEqual(message.message_content, "after")
		self.assertTrue(message.edit_flag)
		self.assertGreaterEqual(message.updated_at, original_updated_at)


class MessageFormTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sender = user_model.objects.create_user(
			username="sender",
			email="sender@example.com",
			password="password123",
		)
		cls.receiver = user_model.objects.create_user(
			username="receiver",
			email="receiver@example.com",
			password="password123",
		)
		cls.product = Product.objects.create(
			item_name="Banana",
			number=10,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="Desc",
			user=cls.sender,
		)
		cls.other_product = Product.objects.create(
			item_name="Apple",
			number=5,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="Desc",
			user=cls.sender,
		)

	def test_message_form_strips_and_validates_content(self):
		form = MessageForm(data={"message_content": "  ", "item": self.product.pk})
		self.assertFalse(form.is_valid())
		self.assertIn("message_content", form.errors)

		form = MessageForm(data={"message_content": "  hello  "})
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data["message_content"], "hello")

	def test_message_form_item_optional(self):
		form = MessageForm(data={"message_content": "hello"})
		self.assertTrue(form.is_valid())

	def test_message_form_widget_attributes(self):
		form = MessageForm()
		widget = form.fields["message_content"].widget
		self.assertEqual(widget.attrs.get("rows"), 2)
		self.assertEqual(form.fields["item"].widget.attrs.get("class"), "form-select")

	def test_message_edit_form_validation_and_widget(self):
		form = MessageEditForm(data={"message_content": " \n"})
		self.assertFalse(form.is_valid())
		self.assertIn("message_content", form.errors)

		form = MessageEditForm(data={"message_content": "  edit  "})
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data["message_content"], "edit")
		self.assertEqual(form.fields["message_content"].widget.attrs.get("rows"), 3)

	def test_conversation_start_form_receiver_queryset_and_labels(self):
		form = ConversationStartForm(user=self.sender)
		receiver_qs = form.fields["receiver"].queryset
		self.assertNotIn(self.sender, receiver_qs)
		self.assertEqual(list(receiver_qs), [self.receiver])
		self.assertEqual(form.fields["receiver"].widget.attrs.get("class"), "form-select")
		self.assertEqual(form.fields["item"].widget.attrs.get("class"), "form-select")

		label = form.fields["receiver"].label_from_instance(self.receiver)
		self.assertIn("receiver", label)

	def test_conversation_start_form_item_queryset_sorted_and_optional(self):
		form = ConversationStartForm(user=self.sender)
		items = list(form.fields["item"].queryset)
		self.assertEqual(items, [self.other_product, self.product])
		self.assertFalse(form.fields["item"].required)


class ConversationViewTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.user = user_model.objects.create_user(
			username="user",
			email="user@example.com",
			password="password123",
			role="consumer",
		)
		cls.producer = user_model.objects.create_user(
			username="producer",
			email="producer@example.com",
			password="password123",
			role="producer",
		)
		cls.other_consumer = user_model.objects.create_user(
			username="other",
			email="other@example.com",
			password="password123",
			role="consumer",
		)
		cls.third_user = user_model.objects.create_user(
			username="third",
			email="third@example.com",
			password="password123",
			role="producer",
		)
		cls.thread_product = Product.objects.create(
			item_name="Thread",
			number=1,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="thread product",
			user=cls.producer,
		)
		cls.user_product = Product.objects.create(
			item_name="UserProduct",
			number=1,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="user product",
			user=cls.user,
		)
		cls.third_product = Product.objects.create(
			item_name="ThirdProduct",
			number=1,
			start_time=timezone.now(),
			end_time=timezone.now() + timedelta(days=1),
			description="third product",
			user=cls.third_user,
		)

	def test_conversation_list_requires_login(self):
		url = reverse("comunicate:conversation_list")
		response = self.client.get(url)
		expected = f"{resolve_url(settings.LOGIN_URL)}?next={url}"
		self.assertRedirects(response, expected, fetch_redirect_response=False)

	def test_conversation_list_authenticated(self):
		Message.objects.create(
			send_user=self.producer,
			receive_user=self.user,
			message_content="hello",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("comunicate:conversation_list"))
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "comunicate/conversation_list.html")

	def test_conversation_detail_requires_login(self):
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.producer.username})
		response = self.client.get(url)
		expected = f"{resolve_url(settings.LOGIN_URL)}?next={url}"
		self.assertRedirects(response, expected, fetch_redirect_response=False)

	def test_conversation_detail_redirects_when_self(self):
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.user.username})
		response = self.client.get(url)
		self.assertRedirects(response, reverse("comunicate:conversation_list"))

	def test_conversation_detail_forbidden_counterpart(self):
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.other_consumer.username})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 404)

	def test_conversation_detail_marks_unread_without_item(self):
		message = Message.objects.create(
			send_user=self.producer,
			receive_user=self.user,
			message_content="hello",
			read_flag=False,
		)
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.producer.username})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		message.refresh_from_db()
		self.assertTrue(message.read_flag)

	def test_conversation_detail_marks_unread_with_item(self):
		message = Message.objects.create(
			send_user=self.producer,
			receive_user=self.user,
			message_content="hello",
			item=self.thread_product,
			read_flag=False,
		)
		self.client.force_login(self.user)
		url = reverse(
			"comunicate:conversation_detail_item",
			kwargs={"username": self.producer.username, "item_id": self.thread_product.pk},
		)
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		message.refresh_from_db()
		self.assertTrue(message.read_flag)

	def test_conversation_detail_disallows_third_party_product(self):
		self.client.force_login(self.user)
		url = reverse(
			"comunicate:conversation_detail_item",
			kwargs={"username": self.producer.username, "item_id": self.third_product.pk},
		)
		response = self.client.get(url)
		self.assertEqual(response.status_code, 404)

	def test_conversation_detail_post_creates_message(self):
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.producer.username})
		response = self.client.post(url, {"message_content": "hi", "item": ""})
		self.assertRedirects(response, url)
		message = Message.objects.get(send_user=self.user, receive_user=self.producer)
		self.assertEqual(message.message_content, "hi")

	def test_conversation_detail_post_uses_selected_item(self):
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.producer.username})
		response = self.client.post(url, {"message_content": "select", "item": self.user_product.pk})
		self.assertRedirects(response, url)
		message = Message.objects.get(send_user=self.user, receive_user=self.producer)
		self.assertEqual(message.item, self.user_product)

	def test_conversation_detail_item_post_uses_thread_item(self):
		self.client.force_login(self.user)
		url = reverse(
			"comunicate:conversation_detail_item",
			kwargs={"username": self.producer.username, "item_id": self.thread_product.pk},
		)
		response = self.client.post(url, {"message_content": "from thread"})
		self.assertRedirects(response, url)
		message = Message.objects.get(send_user=self.user, receive_user=self.producer)
		self.assertEqual(message.item, self.thread_product)

	def test_conversation_detail_post_validation_error(self):
		self.client.force_login(self.user)
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.producer.username})
		response = self.client.post(url, {"message_content": " ", "item": ""})
		self.assertEqual(response.status_code, 200)
		self.assertIn("message_content", response.context["form"].errors)
		self.assertEqual(Message.objects.count(), 0)


class MessageEditViewTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sender = user_model.objects.create_user(
			username="editor",
			email="editor@example.com",
			password="password123",
		)
		cls.receiver = user_model.objects.create_user(
			username="viewer",
			email="viewer@example.com",
			password="password123",
		)
		cls.other_user = user_model.objects.create_user(
			username="intruder",
			email="intruder@example.com",
			password="password123",
		)

	def _create_message(self, **kwargs):
		defaults = {
			"send_user": self.sender,
			"receive_user": self.receiver,
			"message_content": "before",
		}
		defaults.update(kwargs)
		return Message.objects.create(**defaults)

	def test_message_edit_requires_login(self):
		message = self._create_message()
		url = reverse("comunicate:message_edit", kwargs={"pk": message.pk})
		response = self.client.get(url)
		expected = f"{resolve_url(settings.LOGIN_URL)}?next={url}"
		self.assertRedirects(response, expected, fetch_redirect_response=False)

	def test_message_edit_blocks_non_sender(self):
		message = self._create_message()
		url = reverse("comunicate:message_edit", kwargs={"pk": message.pk})
		self.client.force_login(self.other_user)
		response = self.client.get(url)
		self.assertRedirects(response, reverse("comunicate:conversation_list"))
		response = self.client.post(url, {"message_content": "after"})
		self.assertRedirects(response, reverse("comunicate:conversation_list"))
		message.refresh_from_db()
		self.assertEqual(message.message_content, "before")

	def test_message_edit_get_for_sender(self):
		message = self._create_message()
		url = reverse("comunicate:message_edit", kwargs={"pk": message.pk})
		self.client.force_login(self.sender)
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "comunicate/message_edit.html")
		self.assertEqual(response.context["message"].pk, message.pk)

	def test_message_edit_post_updates(self):
		message = self._create_message()
		url = reverse("comunicate:message_edit", kwargs={"pk": message.pk})
		self.client.force_login(self.sender)
		response = self.client.post(url, {"message_content": "after"}, follow=True)
		expected_redirect = f"{reverse('comunicate:conversation_list')}?user={self.receiver.username}"
		self.assertRedirects(response, expected_redirect)
		message.refresh_from_db()
		self.assertEqual(message.message_content, "after")
		self.assertTrue(message.edit_flag)
		flash_messages = list(response.context["messages"])
		self.assertTrue(any("更新しました" in str(msg) for msg in flash_messages))


class MessageDeleteViewTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.sender = user_model.objects.create_user(
			username="deleter",
			email="deleter@example.com",
			password="password123",
		)
		cls.receiver = user_model.objects.create_user(
			username="target",
			email="target@example.com",
			password="password123",
		)
		cls.other_user = user_model.objects.create_user(
			username="outsider",
			email="outsider@example.com",
			password="password123",
		)

	def _create_message(self, **kwargs):
		defaults = {
			"send_user": self.sender,
			"receive_user": self.receiver,
			"message_content": "content",
		}
		defaults.update(kwargs)
		return Message.objects.create(**defaults)

	def test_message_delete_requires_login(self):
		message = self._create_message()
		url = reverse("comunicate:message_delete", kwargs={"pk": message.pk})
		response = self.client.post(url)
		expected = f"{resolve_url(settings.LOGIN_URL)}?next={url}"
		self.assertRedirects(response, expected, fetch_redirect_response=False)

	def test_message_delete_blocks_non_sender(self):
		message = self._create_message()
		url = reverse("comunicate:message_delete", kwargs={"pk": message.pk})
		self.client.force_login(self.other_user)
		response = self.client.post(url)
		self.assertRedirects(response, reverse("comunicate:conversation_list"))
		message.refresh_from_db()
		self.assertFalse(message.delete_flag)

	def test_message_delete_marks_flag_and_sets_message(self):
		message = self._create_message()
		url = reverse("comunicate:message_delete", kwargs={"pk": message.pk})
		self.client.force_login(self.sender)
		response = self.client.post(url)
		expected_redirect = f"{reverse('comunicate:conversation_list')}?user={self.receiver.username}"
		self.assertRedirects(response, expected_redirect)
		message.refresh_from_db()
		self.assertTrue(message.delete_flag)
		flash_messages = list(get_messages(response.wsgi_request))
		self.assertTrue(any("削除しました" in str(msg) for msg in flash_messages))
=======
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Message
from .forms import MessageForm
from django.urls import reverse

class ComunicateAppTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.u1 = User.objects.create_user(username="u1", password="pw", role="consumer")
        self.u2 = User.objects.create_user(username="u2", password="pw", role="producer")

    def test_message_model_methods(self):
        """
        # テスト関数名: test_message_model_methods
        # 対象URL: なし（モデルメソッドテスト）
        # テスト観点: メソッドの動作確認
        # 入力値: メッセージの作成、編集、削除
        # 期待結果: 各メソッドが正しく動作する
        """
        msg = Message.objects.create(send_user=self.u1, receive_user=self.u2, message_content="hello")
        self.assertFalse(msg.read_flag)
        msg.mark_as_read()
        msg.refresh_from_db()
        self.assertTrue(msg.read_flag)
        msg.mark_as_deleted()
        msg.refresh_from_db()
        self.assertTrue(msg.delete_flag)
        msg.record_edit("edited")
        msg.refresh_from_db()
        self.assertEqual(msg.message_content, "edited")
        self.assertTrue(msg.edit_flag)

    def test_messageform_validation_empty(self):
        """
        # テスト関数名: test_messageform_validation_empty
        # 対象URL: なし（フォームテスト）
        # テスト観点: 入力値の検証
        # 入力値: 空のメッセージ
        # 期待結果: フォームが無効になる
        """
        form = MessageForm(data={"message_content": "    "})
        self.assertFalse(form.is_valid())
        self.assertIn("message_content", form.errors)

class ComunicateViewIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.u1 = User.objects.create_user(username="u1v", password="pw", role="consumer")
        self.u2 = User.objects.create_user(username="u2v", password="pw", role="producer")
        self.msg = Message.objects.create(send_user=self.u2, receive_user=self.u1, message_content="hi")

    def test_conversation_detail_marks_read(self):
        """
        # テスト関数名: test_conversation_detail_marks_read
        # 対象URL: comunicate:conversation_detail
        # テスト観点: GETリクエストのレスポンス確認
        # 入力値: ログインユーザー（consumer）
        # 期待結果: ステータスコード200、メッセージが既読になる
        """
        self.client.login(username="u1v", password="pw")
        url = reverse("comunicate:conversation_detail", kwargs={"username": self.u2.username})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.msg.refresh_from_db()
        self.assertTrue(self.msg.read_flag)

    def test_conversation_post_creates_message(self):
        """
        # テスト関数名: test_conversation_post_creates_message
        # 対象URL: comunicate:conversation_detail
        # テスト観点: POSTリクエストによるメッセージ送信確認
        # 入力値: ログインユーザー（consumer）、返信メッセージ
        # 期待結果: ステータスコード302、メッセージがデータベースに作成される
        """
        self.client.login(username="u1v", password="pw")
        url = reverse("comunicate:conversation_detail", kwargs={"username": self.u2.username})
        resp = self.client.post(url, data={"message_content": "reply"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Message.objects.filter(message_content__icontains="reply").exists())
