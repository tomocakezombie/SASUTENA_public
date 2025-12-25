from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from login.models import CustomUser

from product.mentions import extract_mentions, sync_comment_mentions
from product.models import Product, ProductComment, ProductCommentMention


class ProductCommentMentionTests(TestCase):
    def setUp(self) -> None:
        self.author = CustomUser.objects.create_user(username="author", password="pass")
        self.mentioned = CustomUser.objects.create_user(username="mention_target", password="pass")
        self.other_user = CustomUser.objects.create_user(username="other_user", password="pass")
        now = timezone.now()
        self.product = Product.objects.create(
            item_name="Sample",
            number=1,
            start_time=now,
            end_time=now + timedelta(days=1),
            description="Desc",
            user=self.author,
        )

    def test_extract_mentions_returns_unique_usernames(self) -> None:
        content = "Hello @mention_target and @mention_target again"
        usernames = extract_mentions(content)
        self.assertEqual(usernames, {"mention_target"})

    def test_sync_comment_mentions_creates_records(self) -> None:
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @mention_target",
        )
        sync_comment_mentions(comment)
        mentions = ProductCommentMention.objects.filter(comment=comment)
        self.assertEqual(mentions.count(), 1)
        self.assertEqual(mentions.first().mentioned_user, self.mentioned)

    def test_sync_comment_mentions_ignores_unknown_users(self) -> None:
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @ghost",
        )
        sync_comment_mentions(comment)
        self.assertFalse(ProductCommentMention.objects.filter(comment=comment).exists())

    def test_sync_comment_mentions_updates_on_edit(self) -> None:
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.author,
            content="Hi @mention_target",
        )
        sync_comment_mentions(comment)
        comment.content = "Ping @other_user"
        comment.save(update_fields=["content"])
        sync_comment_mentions(comment)
        mentions = ProductCommentMention.objects.filter(comment=comment)
        self.assertEqual(mentions.count(), 1)
        self.assertEqual(mentions.first().mentioned_user, self.other_user)

    def test_sync_comment_mentions_removes_when_no_mentions(self) -> None:
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
