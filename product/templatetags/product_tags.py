from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from ..mentions import MENTION_PATTERN

register = template.Library()


@register.filter(name="render_mentions", needs_autoescape=True)
def render_mentions(value: str | None, autoescape: bool = True) -> str:
    if not value:
        return ""

    escape = conditional_escape if autoescape else lambda x: x
    text = escape(value)

    def _replace(match):
        username = match.group("username")
        try:
            url = reverse("accounts:profile_detail", args=[username])
        except NoReverseMatch:
            return f"@{username}"
        return format_html('<a class="mention-link" href="{0}">@{1}</a>', url, username)

    replaced = MENTION_PATTERN.sub(_replace, text)
    return mark_safe(replaced.replace("\n", "<br>"))
