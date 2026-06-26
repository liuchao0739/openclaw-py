"""Normalizes outbound message text to suppress duplicate send actions.

Mirrors src/agents/embedded-agent-helpers/messaging-dedupe.ts.
"""

from __future__ import annotations

import re

MIN_DUPLICATE_TEXT_LENGTH = 10
MIN_REVERSE_SUBSTRING_DUPLICATE_RATIO = 0.5


def _normalize_lowercase_or_empty(text: str) -> str:
    return text.strip().lower() if isinstance(text, str) else ""


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for duplicate comparison."""
    result = _normalize_lowercase_or_empty(text)
    result = re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F300-\U0001F9FF]", "", result)
    result = re.sub(r"\s+", " ", result)
    return result.strip()


def is_messaging_tool_duplicate_normalized(
    normalized: str,
    normalized_sent_texts: list[str],
) -> bool:
    """Compare already-normalized message text against prior sends."""
    if not normalized_sent_texts:
        return False
    if not normalized or len(normalized) < MIN_DUPLICATE_TEXT_LENGTH:
        return False
    return any(
        bool(normalized_sent)
        and len(normalized_sent) >= MIN_DUPLICATE_TEXT_LENGTH
        and (
            normalized_sent in normalized
            or (
                normalized in normalized_sent
                and len(normalized) >= len(normalized_sent) * MIN_REVERSE_SUBSTRING_DUPLICATE_RATIO
            )
        )
        for normalized_sent in normalized_sent_texts
    )


def is_messaging_tool_duplicate(text: str, sent_texts: list[str]) -> bool:
    """Return True when raw message text duplicates a prior sent message."""
    if not sent_texts:
        return False
    normalized = normalize_text_for_comparison(text)
    if not normalized or len(normalized) < MIN_DUPLICATE_TEXT_LENGTH:
        return False
    return is_messaging_tool_duplicate_normalized(
        normalized,
        [normalize_text_for_comparison(t) for t in sent_texts],
    )
