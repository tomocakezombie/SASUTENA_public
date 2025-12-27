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
