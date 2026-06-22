"""CJK-aware character counting for token estimation."""

from __future__ import annotations

import re

CHARS_PER_TOKEN_ESTIMATE = 4

_NON_LATIN_RE = re.compile(
    r"[\u2E80-\u9FFF\uA000-\uA4FF\uAC00-\uD7AF\uF900-\uFAFF"
    r"\U00020000-\U0002FA1F]",
    re.UNICODE,
)
_CJK_SURROGATE_HIGH_RE = re.compile(r"[\uD840-\uD87E][\uDC00-\uDFFF]")


def _count_code_points(text: str, non_latin_count: int) -> int:
    if non_latin_count == 0:
        return len(text)
    cjk_surrogates = len(_CJK_SURROGATE_HIGH_RE.findall(text))
    return len(text) - cjk_surrogates


def estimate_string_chars(text: str) -> int:
    if len(text) == 0:
        return 0
    non_latin_count = len(_NON_LATIN_RE.findall(text))
    code_point_length = _count_code_points(text, non_latin_count)
    return code_point_length + non_latin_count * (CHARS_PER_TOKEN_ESTIMATE - 1)


def estimate_tokens_from_chars(chars: int) -> int:
    return (max(0, chars) + CHARS_PER_TOKEN_ESTIMATE - 1) // CHARS_PER_TOKEN_ESTIMATE