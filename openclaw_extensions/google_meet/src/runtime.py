"""Google Meet plugin module implements runtime behavior."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from openclaw.packages.normalization_core import normalize_optional_string

_MEETING_CODE_PATH_RE = re.compile(r"^/[a-z]{3}-[a-z]{4}-[a-z]{3}(?:$|[/?#])", re.IGNORECASE)


def normalize_meet_url(input_value: Any) -> str:
    raw = normalize_optional_string(input_value)
    if not raw:
        raise ValueError("url required")
    try:
        parsed = urlparse(raw)
    except Exception:
        raise ValueError("url must be a valid Google Meet URL")
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "meet.google.com":
        raise ValueError("url must be an explicit https://meet.google.com/... URL")
    if not _MEETING_CODE_PATH_RE.match(parsed.path):
        raise ValueError("url must include a Google Meet meeting code")
    return urlunparse(parsed)
