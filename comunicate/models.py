from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models


class Message(models.Model):
	message_id = models.BigAutoField(primary_key=True)
	send_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="sent_messages",
		db_column="send_user_id",
	)
	receive_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="received_messages",
		db_column="receive_user_id",
	)
	message_content = models.CharField(
		max_length=511,
		validators=[MinLengthValidator(1)],
	)
	send_time = models.DateTimeField(auto_now_add=True)
	read_flag = models.BooleanField(default=False)
	delete_flag = models.BooleanField(default=False)
	item = models.ForeignKey(
		"product.Product",
		on_delete=models.CASCADE,
		related_name="messages",
		db_column="item_id",
		null=True,
		blank=True,
	)
	edit_flag = models.BooleanField(default=False)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-send_time"]

	def mark_as_read(self):
		if not self.read_flag:
			self.read_flag = True
			self.save(update_fields=["read_flag"])

	def mark_as_deleted(self):
		if not self.delete_flag:
			self.delete_flag = True
			self.save(update_fields=["delete_flag"])

	def record_edit(self, content):
		self.message_content = content
		self.edit_flag = True
		self.save(update_fields=["message_content", "edit_flag", "updated_at"])

	def __str__(self):
		return f"{self.message_id}: {self.send_user} -> {self.receive_user}"
