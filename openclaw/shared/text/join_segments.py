from __future__ import annotations

from typing import Optional


def concat_optional_text_segments(
    left: Optional[str] = None,
    right: Optional[str] = None,
    separator: str = "\n\n",
) -> Optional[str]:
    if left and right:
        return f"{left}{separator}{right}"
    return right or left


def join_present_text_segments(
    segments: list[Optional[str]],
    separator: str = "\n\n",
    trim: bool = False,
) -> Optional[str]:
    values: list[str] = []
    for segment in segments:
        if not isinstance(segment, str):
            continue
        normalized = segment.strip() if trim else segment
        if not normalized:
            continue
        values.append(normalized)
    return separator.join(values) if values else None
