from typing import Optional, Sequence

from bs4 import BeautifulSoup

from pymess.config import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def find_banned_tag(html_body: str, banned_tags: Sequence[str] = None) -> Optional[str]:
    banned_tags = banned_tags if banned_tags is not None else settings.EMAIL_TEMPLATE_BANNED_TAGS
    soup = BeautifulSoup(html_body, 'html.parser')
    return next((tag for tag in banned_tags if soup.find(tag)), None)


def raise_error_if_contains_banned_tags(html_body) -> str:
    """
    Raises a `ValidationError` if a `html_body` contains banned tags or attributes. Otherwise returns the `html_body`.
    """
    tag = find_banned_tag(html_body)
    if tag:
        raise ValidationError(
            _('HTML body contains one of banned tag: {}').format(tag))
    return html_body
