from __future__ import annotations

import re
from typing import List, Tuple


def _resolve_chunk_early_return(text: str, limit: int):
    if not text:
        return []
    if limit <= 0:
        return [text]
    if len(text) <= limit:
        return [text]
    return None


def _scan_paren_aware_breakpoints(text: str) -> Tuple[int, int]:
    last_newline = -1
    last_whitespace = -1
    depth = 0

    for ch in text:
        if ch == "(":
            depth += 1
            continue
        if ch == ")" and depth > 0:
            depth -= 1
            continue
        if depth != 0:
            continue
        if ch == "\n":
            last_newline = text.index(ch, last_newline + 1) if last_newline >= 0 else -1
            last_newline = text.find("\n", 0)
        elif ch.isspace():
            last_whitespace = text.find(ch, last_whitespace + 1) if last_whitespace >= 0 else -1
    return last_newline, last_whitespace


def _scan_paren_aware_breakpoints_at(text: str) -> Tuple[int, int]:
    last_newline = -1
    last_whitespace = -1
    depth = 0

    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
            continue
        if ch == ")" and depth > 0:
            depth -= 1
            continue
        if depth != 0:
            continue
        if ch == "\n":
            last_newline = i
        elif ch.isspace():
            last_whitespace = i
    return last_newline, last_whitespace


def avoid_trailing_high_surrogate_break(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return end
    if end - 1 < 0 or end >= len(text):
        return end
    try:
        cp_prev = ord(text[end - 1])
        cp_cur = ord(text[end])
    except (IndexError, TypeError):
        return end
    if not (0xD800 <= cp_prev <= 0xDBFF and 0xDC00 <= cp_cur <= 0xDFFF):
        return end
    return end - 1 if end - 1 > start else end + 1


def chunk_text(text: str, limit: int) -> List[str]:
    early = _resolve_chunk_early_return(text, limit)
    if early is not None:
        return early

    chunks: List[str] = []
    cursor = 0
    while cursor < len(text):
        if len(text) - cursor <= limit:
            chunks.append(text[cursor:])
            break
        window_end = min(len(text), cursor + limit)
        window = text[cursor:window_end]
        last_newline, last_whitespace = _scan_paren_aware_breakpoints_at(window)
        break_offset = last_newline if last_newline > 0 else last_whitespace
        end = avoid_trailing_high_surrogate_break(
            text,
            cursor,
            cursor + break_offset if break_offset > 0 else window_end,
        )
        chunks.append(text[cursor:end])
        cursor = end
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
    return chunks
