"""Text chunking helpers split text into bounded chunks with safe break points."""

from __future__ import annotations

from typing import Any, Callable


def avoid_trailing_high_surrogate_break(text: str, start: int, end: int) -> int:
    if end <= start or end >= len(text):
        return end
    previous = ord(text[end - 1])
    next_char = ord(text[end])
    splits_surrogate_pair = (
        0xD800 <= previous <= 0xDBFF and 0xDC00 <= next_char <= 0xDFFF
    )
    if not splits_surrogate_pair:
        return end
    adjusted = end - 1
    return adjusted if adjusted > start else end + 1


def chunk_text_by_break_resolver(
    text: str,
    limit: int,
    resolve_break_index: Callable[[str], int],
) -> list[str]:
    if not text:
        return []
    if limit <= 0 or len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        candidate_break = resolve_break_index(window)
        if candidate_break > 0 and candidate_break <= limit:
            break_idx = candidate_break
        else:
            break_idx = limit
        safe_break = avoid_trailing_high_surrogate_break(remaining, 0, break_idx)
        raw_chunk = remaining[:safe_break]
        chunk = raw_chunk.rstrip()
        if len(chunk) > 0:
            chunks.append(chunk)
        broke_on_separator = safe_break < len(remaining) and remaining[safe_break].isspace()
        next_start = min(len(remaining), safe_break + (1 if broke_on_separator else 0))
        remaining = remaining[next_start:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks
