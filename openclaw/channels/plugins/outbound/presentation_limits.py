"""Presentation limit adapters for channel outbound payloads.

Truncates and reshapes portable presentation blocks to match per-channel limits.
"""

from __future__ import annotations

from typing import Any


def _positive_integer(value: int | None) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def truncate_text(value: str, max_length: int | None) -> str:
    """Truncate text to max_length characters."""
    limit = _positive_integer(max_length)
    if not limit:
        return value
    return value[:limit] if len(value) > limit else value


def _utf8_byte_length(value: str) -> int:
    return len(value.encode("utf-8"))


def truncate_utf8_bytes(value: str, limit: int) -> str:
    """Truncate text to fit within a UTF-8 byte limit."""
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    truncated = encoded[:limit].decode("utf-8", errors="ignore")
    return truncated


def truncate_presentation_text(
    value: str,
    max_length: int | None = None,
    encoding: str | None = None,
) -> str:
    """Truncate presentation text respecting encoding constraints."""
    limit = _positive_integer(max_length)
    if not limit:
        return value
    if encoding == "utf8-bytes":
        return truncate_utf8_bytes(value, limit)
    if encoding == "utf16-units":
        return value[:limit] if len(value) > limit else value
    return value[:limit] if len(value) > limit else value


def fits_byte_limit(value: str | None, max_bytes: int | None) -> bool:
    """Check if a value fits within a byte limit."""
    limit = _positive_integer(max_bytes)
    if not value or not limit:
        return True
    return _utf8_byte_length(value) <= limit


def action_capacity(
    max_actions: int | None = None,
    max_rows: int | None = None,
    max_actions_per_row: int | None = None,
) -> int | None:
    """Compute total action capacity from row/action limits."""
    ma = _positive_integer(max_actions)
    mr = _positive_integer(max_rows)
    mapr = _positive_integer(max_actions_per_row)
    row_capacity = mr * mapr if mr and mapr else None
    if ma and row_capacity:
        return min(ma, row_capacity)
    return ma or row_capacity


def fallback_list_block(
    block_type: str,
    heading: str,
    labels: list[str],
    max_label_length: int | None = None,
) -> dict[str, Any] | None:
    """Create a fallback list block from labels."""
    truncated = [truncate_text(label, max_label_length) for label in labels if label and label.strip()]
    if not truncated:
        return None
    return {
        "type": block_type,
        "text": f"{heading}:\n" + "\n".join(f"- {label}" for label in truncated),
    }
