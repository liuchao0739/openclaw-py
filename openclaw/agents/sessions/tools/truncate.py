"""Session tool truncation facade.

Re-exports shared truncation utilities. When the agent-core harness truncation
module is not yet ported, local implementations are provided.
"""

from __future__ import annotations

from typing import Any, TypedDict

DEFAULT_MAX_BYTES = 30_000
DEFAULT_MAX_LINES = 500
GREP_MAX_LINE_LENGTH = 2000


class TruncationOptions(TypedDict, total=False):
    maxLines: int
    maxBytes: int


class TruncationResult(TypedDict, total=False):
    content: str
    truncated: bool
    truncatedBy: str | None
    totalLines: int
    totalBytes: int
    maxLines: int
    maxBytes: int


def format_size(bytes_count: int) -> str:
    """Format a byte count as a human-readable string."""
    if bytes_count < 1024:
        return f"{bytes_count}B"
    if bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    return f"{bytes_count / (1024 * 1024):.1f}MB"


def _byte_length(text: str) -> int:
    return len(text.encode("utf-8"))


def truncate_line(text: str, max_length: int = GREP_MAX_LINE_LENGTH) -> str:
    """Truncate a single line to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def truncate_tail(text: str, options: TruncationOptions | None = None) -> TruncationResult:
    """Truncate text from the head, keeping the tail within limits."""
    opts = options or {}
    max_lines = opts.get("maxLines", DEFAULT_MAX_LINES)
    max_bytes = opts.get("maxBytes", DEFAULT_MAX_BYTES)

    lines = text.split("\n")
    total_lines = len(lines)
    total_bytes = _byte_length(text)

    truncated = total_lines > max_lines or total_bytes > max_bytes
    truncated_by: str | None = None
    if truncated:
        truncated_by = "bytes" if total_bytes > max_bytes else "lines"

    if not truncated:
        return TruncationResult(
            content=text,
            truncated=False,
            truncatedBy=None,
            totalLines=total_lines,
            totalBytes=total_bytes,
            maxLines=max_lines,
            maxBytes=max_bytes,
        )

    # Keep the tail within both line and byte limits
    kept_lines: list[str] = []
    kept_bytes = 0
    for line in reversed(lines):
        line_bytes = _byte_length(line) + 1  # +1 for newline
        if kept_bytes + line_bytes > max_bytes or len(kept_lines) >= max_lines:
            break
        kept_lines.insert(0, line)
        kept_bytes += line_bytes

    content = "\n".join(kept_lines)
    return TruncationResult(
        content=content,
        truncated=True,
        truncatedBy=truncated_by,
        totalLines=total_lines,
        totalBytes=total_bytes,
        maxLines=max_lines,
        maxBytes=max_bytes,
    )


def truncate_head(text: str, options: TruncationOptions | None = None) -> TruncationResult:
    """Truncate text from the tail, keeping the head within limits."""
    opts = options or {}
    max_lines = opts.get("maxLines", DEFAULT_MAX_LINES)
    max_bytes = opts.get("maxBytes", DEFAULT_MAX_BYTES)

    lines = text.split("\n")
    total_lines = len(lines)
    total_bytes = _byte_length(text)

    truncated = total_lines > max_lines or total_bytes > max_bytes
    truncated_by: str | None = None
    if truncated:
        truncated_by = "bytes" if total_bytes > max_bytes else "lines"

    if not truncated:
        return TruncationResult(
            content=text,
            truncated=False,
            truncatedBy=None,
            totalLines=total_lines,
            totalBytes=total_bytes,
            maxLines=max_lines,
            maxBytes=max_bytes,
        )

    kept_lines: list[str] = []
    kept_bytes = 0
    for line in lines:
        line_bytes = _byte_length(line) + 1
        if kept_bytes + line_bytes > max_bytes or len(kept_lines) >= max_lines:
            break
        kept_lines.append(line)
        kept_bytes += line_bytes

    content = "\n".join(kept_lines)
    return TruncationResult(
        content=content,
        truncated=True,
        truncatedBy=truncated_by,
        totalLines=total_lines,
        totalBytes=total_bytes,
        maxLines=max_lines,
        maxBytes=max_bytes,
    )
