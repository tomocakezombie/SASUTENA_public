from .models import Message

def unread_message_count(request):
    if request.user.is_authenticated:
        count = Message.objects.filter(
            receive_user=request.user,
            read_flag=False,
            delete_flag=False
        ).count()
    else:
        count = 0

    return {
        "unread_message_count": count
    }
