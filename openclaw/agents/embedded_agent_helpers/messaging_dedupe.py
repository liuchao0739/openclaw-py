"""Normalize outbound message text to suppress duplicate send actions."""

from __future__ import annotations

import re
MIN_DUPLICATE_TEXT_LENGTH = 10
MIN_REVERSE_SUBSTRING_DUPLICATE_RATIO = 0.5

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text)


def normalize_text_for_comparison(text: str) -> str:
    lowered = text.strip().lower()
    no_emoji = _strip_emoji(lowered)
    collapsed = re.sub(r"\s+", " ", no_emoji).strip()
    return collapsed


def is_messaging_tool_duplicate_normalized(
    normalized: str,
    normalized_sent_texts: list[str],
) -> bool:
    if not normalized_sent_texts:
        return False
    if not normalized or len(normalized) < MIN_DUPLICATE_TEXT_LENGTH:
        return False
    for normalized_sent in normalized_sent_texts:
        if not normalized_sent or len(normalized_sent) < MIN_DUPLICATE_TEXT_LENGTH:
            continue
        if normalized_sent in normalized:
            return True
        if normalized in normalized_sent and len(normalized) >= len(
            normalized_sent
        ) * MIN_REVERSE_SUBSTRING_DUPLICATE_RATIO:
            return True
    return False


def is_messaging_tool_duplicate(text: str, sent_texts: list[str]) -> bool:
    if not sent_texts:
        return False
    normalized = normalize_text_for_comparison(text)
    if not normalized or len(normalized) < MIN_DUPLICATE_TEXT_LENGTH:
        return False
    sent_normalized = [normalize_text_for_comparison(t) for t in sent_texts]
    return is_messaging_tool_duplicate_normalized(normalized, sent_normalized)