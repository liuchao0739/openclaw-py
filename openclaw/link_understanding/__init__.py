"""Link understanding package — defaults, format, detection."""

from .defaults import DEFAULT_LINK_TIMEOUT_SECONDS, DEFAULT_MAX_LINKS
from .format import format_link_understanding_body
from .detect import extract_links_from_message

__all__ = [
    "DEFAULT_LINK_TIMEOUT_SECONDS",
    "DEFAULT_MAX_LINKS",
    "format_link_understanding_body",
    "extract_links_from_message",
]
