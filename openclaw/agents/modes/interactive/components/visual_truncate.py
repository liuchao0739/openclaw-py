"""Truncate text to a maximum number of visual lines (word-wrap aware)."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class VisualTruncateResult:
    visual_lines: list[str]
    skipped_count: int


def _wrap_line(line: str, width: int, padding_x: int) -> list[str]:
    effective = max(1, width - 2 * padding_x)
    if not line:
        return [""]
    segments = line.split("\n")
    out: list[str] = []
    for segment in segments:
        if len(segment) <= effective:
            out.append(segment)
        else:
            out.extend(textwrap.wrap(segment, width=effective, break_long_words=True, break_on_hyphens=False) or [""])
    return out


def truncate_to_visual_lines(
    text: str,
    max_visual_lines: int,
    width: int,
    padding_x: int = 0,
) -> VisualTruncateResult:
    if not text:
        return VisualTruncateResult(visual_lines=[], skipped_count=0)

    all_visual: list[str] = []
    for raw_line in text.split("\n"):
        all_visual.extend(_wrap_line(raw_line, width, padding_x))

    if len(all_visual) <= max_visual_lines:
        return VisualTruncateResult(visual_lines=all_visual, skipped_count=0)

    truncated = all_visual[-max_visual_lines:]
    skipped = len(all_visual) - max_visual_lines
    return VisualTruncateResult(visual_lines=truncated, skipped_count=skipped)