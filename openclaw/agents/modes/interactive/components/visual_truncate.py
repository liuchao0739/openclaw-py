"""Shared utility for truncating text to visual lines (accounting for line wrapping).

Mirrors src/agents/modes/interactive/components/visual-truncate.ts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisualTruncateResult:
    visual_lines: list[str]
    skipped_count: int


def _wrap_line(line: str, width: int) -> list[str]:
    """Wrap a single line to the given width."""
    if width <= 0:
        return [line]
    if len(line) <= width:
        return [line]
    result: list[str] = []
    for i in range(0, len(line), width):
        result.append(line[i : i + width])
    return result


def truncate_to_visual_lines(
    text: str,
    max_visual_lines: int,
    width: int,
    padding_x: int = 0,
) -> VisualTruncateResult:
    """Truncate text to a maximum number of visual lines (from the end).

    Args:
        text: The text content (may contain newlines)
        max_visual_lines: Maximum number of visual lines to show
        width: Terminal/render width
        padding_x: Horizontal padding (default 0)
    """
    if not text:
        return VisualTruncateResult(visual_lines=[], skipped_count=0)

    effective_width = max(1, width - padding_x * 2)
    all_visual_lines: list[str] = []
    for line in text.split("\n"):
        all_visual_lines.extend(_wrap_line(line, effective_width))

    if len(all_visual_lines) <= max_visual_lines:
        return VisualTruncateResult(visual_lines=all_visual_lines, skipped_count=0)

    truncated = all_visual_lines[-max_visual_lines:]
    skipped = len(all_visual_lines) - max_visual_lines
    return VisualTruncateResult(visual_lines=truncated, skipped_count=skipped)
