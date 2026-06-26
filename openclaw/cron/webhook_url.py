"""Normalizes cron webhook destination URLs.

Mirrors src/cron/webhook-url.ts.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _is_allowed_webhook_protocol(protocol: str) -> bool:
    return protocol in ("http", "https")


def normalize_http_webhook_url(value: Any) -> str | None:
    """Normalize cron webhook URLs.

    Rejects empty, malformed, and non-HTTP(S) values. Returns ``None`` on
    rejection, otherwise the trimmed URL string.
    """
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        parsed = urlparse(trimmed)
    except Exception:
        return None
    if not _is_allowed_webhook_protocol(parsed.scheme):
        return None
    # urlparse returns empty scheme for malformed URLs without scheme
    if not parsed.scheme:
        return None
    return trimmed
