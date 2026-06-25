"""Small progress-draft line helpers shared by streaming renderers."""

from __future__ import annotations

from typing import Any


def remove_channel_progress_draft_line(
    lines: list[Any],
    line_id: str,
) -> list[Any]:
    """Remove a keyed structured progress line while preserving plain text draft lines.

    Returns the original list when no line is removed so renderers can use identity
    as a no-op signal.
    """
    trimmed_id = line_id.strip() if line_id else ""
    if not trimmed_id:
        return lines

    next_lines = [
        line for line in lines
        if not (
            isinstance(line, dict)
            and isinstance(line.get("id"), str)
            and line["id"].strip() == trimmed_id
        )
    ]
    return next_lines if len(next_lines) != len(lines) else lines
