import re
from typing import Set

from django.contrib.auth import get_user_model

from .models import ProductComment, ProductCommentMention

MENTION_PATTERN = re.compile(r"@(?P<username>[A-Za-z0-9_]+)")


def extract_mentions(content: str) -> Set[str]:
    if not content:
        return set()
    matches = MENTION_PATTERN.findall(content)
    return {match for match in matches}


def sync_comment_mentions(comment: ProductComment, *, content: str | None = None) -> None:
    comment_text = content if content is not None else comment.content
    usernames = extract_mentions(comment_text)
    if not usernames:
        comment.mentions.all().delete()
        return

    User = get_user_model()
    users = list(User.objects.filter(username__in=usernames))
    user_map = {user.username: user for user in users}

    existing_mentions = {
        mention.mentioned_user_id: mention
        for mention in comment.mentions.all()
    }
    desired_user_ids = set()
    for username in usernames:
        user = user_map.get(username)
        if not user:
            continue
        desired_user_ids.add(user.id)
        if user.id not in existing_mentions:
            ProductCommentMention.objects.create(comment=comment, mentioned_user=user)

    for user_id, mention in existing_mentions.items():
        if user_id not in desired_user_ids:
            mention.delete()
