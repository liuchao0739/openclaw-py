from __future__ import annotations

import re


def parse_media_content_length(raw: str | None) -> int | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not re.fullmatch(r"\d+", trimmed):
        raise ValueError(f"invalid content-length header: {raw}")
    try:
        size = int(trimmed)
    except ValueError:
        raise ValueError(f"invalid content-length header: {raw}")
    if not float(size).is_integer() or abs(size) > (2**53 - 1):
        raise ValueError(f"invalid content-length header: {raw}")
    return size
