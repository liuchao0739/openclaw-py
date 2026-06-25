"""Byte-limit helpers for session tool stderr/stdout tails."""

from __future__ import annotations

import math

SESSION_TOOL_STDERR_TAIL_BYTES = 64 * 1024


def normalize_positive_limit(value: int | None, fallback: int) -> int:
    """Normalize optional positive numeric limits to a finite integer."""
    if value is None or not math.isfinite(value):
        return fallback
    return max(1, int(value))


def append_bounded_text_tail(
    current: str,
    chunk: bytes | str,
    max_bytes: int = SESSION_TOOL_STDERR_TAIL_BYTES,
) -> str:
    """Append a chunk while retaining only the UTF-8-safe tail within max_bytes."""
    effective_max_bytes = normalize_positive_limit(max_bytes, SESSION_TOOL_STDERR_TAIL_BYTES)

    if isinstance(chunk, str):
        chunk_bytes = chunk.encode("utf-8")
    else:
        chunk_bytes = chunk

    if len(chunk_bytes) >= effective_max_bytes:
        return _decode_utf8_tail(chunk_bytes, effective_max_bytes)

    current_bytes = current.encode("utf-8")
    next_bytes = len(current_bytes) + len(chunk_bytes)
    if next_bytes <= effective_max_bytes:
        return current + chunk_bytes.decode("utf-8")

    current_tail_bytes = max(0, effective_max_bytes - len(chunk_bytes))
    current_tail = current_bytes[len(current_bytes) - current_tail_bytes:]
    combined = current_tail + chunk_bytes
    return _decode_utf8_tail(combined, effective_max_bytes)


def _decode_utf8_tail(buffer: bytes, max_bytes: int) -> str:
    """Decode the tail of a byte buffer, UTF-8 safe."""
    text = buffer.decode("utf-8", errors="ignore")
    chars = list(text)
    kept: list[str] = []
    total_bytes = 0

    for char in reversed(chars):
        char_bytes = len(char.encode("utf-8"))
        if total_bytes + char_bytes > max_bytes:
            break
        kept.append(char)
        total_bytes += char_bytes

    kept.reverse()
    return "".join(kept)
