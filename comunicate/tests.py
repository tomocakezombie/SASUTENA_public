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
		form = MessageForm(data={"message_content": "    "})
		self.assertFalse(form.is_valid())
		self.assertIn("message_content", form.errors)


class ComunicateViewIntegrationTests(TestCase):
	def setUp(self):
		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.u1 = User.objects.create_user(username="u1v", password="pw", role="consumer")
		self.u2 = User.objects.create_user(username="u2v", password="pw", role="producer")
		self.msg = Message.objects.create(send_user=self.u2, receive_user=self.u1, message_content="hi")

	def test_conversation_detail_marks_read(self):
		self.client.login(username="u1v", password="pw")
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.u2.username})
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.msg.refresh_from_db()
		self.assertTrue(self.msg.read_flag)

	def test_conversation_post_creates_message(self):
		self.client.login(username="u1v", password="pw")
		url = reverse("comunicate:conversation_detail", kwargs={"username": self.u2.username})
		resp = self.client.post(url, data={"message_content": "reply"})
		self.assertEqual(resp.status_code, 302)
		self.assertTrue(Message.objects.filter(message_content__icontains="reply").exists())
