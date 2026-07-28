from __future__ import annotations

import re
from typing import Literal

from .code_regions import find_code_regions, is_inside_code
from .final_tags import find_final_tag_matches

ReasoningTagMode = Literal["strict", "preserve"]
ReasoningTagTrim = Literal["none", "start", "both"]

_QUICK_TAG_RE = re.compile(
    r"<\s*\/?\s*(?:(?:antml:|mm:)?(?:think(?:ing)?|thought)|antthinking|final)\b",
    re.IGNORECASE,
)
_THINKING_TAG_RE = re.compile(
    r"<\s*(\/?)\s*(?:(?:antml:|mm:)?(?:think(?:ing)?|thought)|antthinking)\b[^<>]*>",
    re.IGNORECASE,
)


def _apply_trim(value: str, mode: ReasoningTagTrim) -> str:
    if mode == "none":
        return value
    if mode == "start":
        return value.lstrip()
    return value.strip()


def has_orphan_reasoning_close_boundary(before: str, after: str) -> bool:
    return bool(before.strip() and after.strip())


def strip_reasoning_tags_from_text(
    text: str,
    mode: ReasoningTagMode = "strict",
    trim: ReasoningTagTrim = "both",
) -> str:
    if not text:
        return text
    if not _QUICK_TAG_RE.search(text):
        return text

    cleaned = text
    matches = find_final_tag_matches(cleaned)
    _THINKING_TAG_RE.pattern  # noqa: B018
    has_thinking_tag = bool(_THINKING_TAG_RE.search(cleaned))
    if not matches and not has_thinking_tag:
        return text
    if matches:
        final_matches: list[tuple[int, int, bool]] = []
        pre_code_regions = find_code_regions(cleaned)
        for match in matches:
            start = match.index
            final_matches.append(
                (start, len(match.text), is_inside_code(start, pre_code_regions))
            )

        for m in reversed(final_matches):
            start, length, in_code = m
            if not in_code:
                cleaned = cleaned[:start] + cleaned[start + length :]

    code_regions = find_code_regions(cleaned)

    result: list[str] = []
    last_index = 0
    thinking_depth = 0
    first_unclosed_content_index: int | None = None

    for match in _THINKING_TAG_RE.finditer(cleaned):
        idx = match.start()
        is_close = match.group(1) == "/"

        if is_inside_code(idx, code_regions):
            continue

        if thinking_depth == 0:
            if is_close:
                after_index = idx + len(match.group(0))
                before = cleaned[last_index:idx]
                after = cleaned[after_index:]
                if has_orphan_reasoning_close_boundary(before, after):
                    result = []
                else:
                    result.append(before)
                last_index = after_index
                continue
            result.append(cleaned[last_index:idx])
            thinking_depth = 1
            first_unclosed_content_index = idx + len(match.group(0))
        elif is_close:
            thinking_depth -= 1
            if thinking_depth == 0:
                first_unclosed_content_index = None
        else:
            thinking_depth += 1

        last_index = idx + len(match.group(0))

    if thinking_depth == 0 or mode == "preserve":
        result.append(cleaned[last_index:])

    result_text = "".join(result)
    trimmed_result = _apply_trim(result_text, trim)
    if (
        mode == "strict"
        and thinking_depth > 0
        and not trimmed_result
        and first_unclosed_content_index is not None
        and cleaned.strip()
    ):
        return _apply_trim(cleaned[first_unclosed_content_index:], trim)

    return trimmed_result
