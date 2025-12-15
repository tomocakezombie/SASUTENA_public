from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = (
		"message_id",
		"send_user",
		"receive_user",
		"message_content",
		"send_time",
		"read_flag",
		"delete_flag",
		"edit_flag",
	)
	list_filter = ("read_flag", "delete_flag", "edit_flag", "send_time")
	search_fields = ("message_content", "send_user__username", "receive_user__username")
