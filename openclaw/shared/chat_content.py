"""Coerces provider content values into displayable text and extracts normalized plain text."""

from __future__ import annotations

import json
from typing import Any, Callable


def coerce_chat_content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return ""
    return ""


def extract_text_from_chat_content(
    content: Any,
    sanitize_text: Callable[[str], str] | None = None,
    join_with: str = " ",
    normalize_text: Callable[[str], str] | None = None,
) -> str | None:
    if normalize_text is None:
        def _normalize(text: str) -> str:
            import re
            return re.sub(r"\s+", " ", text).strip()
        normalize_text = _normalize

    def _sanitize(value: Any) -> str:
        raw = coerce_chat_content_text(value)
        sanitized = sanitize_text(raw) if sanitize_text else raw
        return coerce_chat_content_text(sanitized)

    def _normalize(value: Any) -> str:
        return coerce_chat_content_text(normalize_text(coerce_chat_content_text(value)))

    if isinstance(content, str):
        value = _sanitize(content)
        normalized = _normalize(value)
        return normalized if normalized else None

    if not isinstance(content, list):
        return None

    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        value = _sanitize(text)
        if value.strip():
            chunks.append(value)

    joined = _normalize(join_with.join(chunks))
    return joined if joined else None
