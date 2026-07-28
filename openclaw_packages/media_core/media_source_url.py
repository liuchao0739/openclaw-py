from __future__ import annotations

import re

HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
MXC_URL_RE = re.compile(r"^mxc://", re.IGNORECASE)
BUFFER_URL_RE = re.compile(r"^buffer://", re.IGNORECASE)


def is_pass_through_remote_media_source(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    return bool(
        HTTP_URL_RE.match(normalized)
        or MXC_URL_RE.match(normalized)
        or BUFFER_URL_RE.match(normalized)
    )
