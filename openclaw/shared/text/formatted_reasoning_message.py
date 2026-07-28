from __future__ import annotations

import re

from .reasoning_tags import strip_reasoning_tags_from_text

_THINKING_PREFIX_RE = re.compile(r"^Thinking\.{0,3}$")


def strip_formatted_reasoning_message(text: str) -> str:
    stripped = strip_reasoning_tags_from_text(text)
    lines = re.split(r"\r?\n", stripped)
    prefix = lines[0].strip() if lines else ""
    if prefix != "Reasoning:" and not _THINKING_PREFIX_RE.match(prefix):
        return stripped
    if _THINKING_PREFIX_RE.match(prefix):
        first_body_line = next((line for line in lines[1:] if line.strip()), "")
        trimmed_body_line = first_body_line.strip() if first_body_line else ""
        if (
            not trimmed_body_line
            or not (
                trimmed_body_line.startswith("_")
                and trimmed_body_line.endswith("_")
                and len(trimmed_body_line) >= 2
            )
        ):
            return stripped

    index = 1
    while index < len(lines):
        trimmed = lines[index].strip() if index < len(lines) else ""
        if not trimmed or (
            trimmed.startswith("_")
            and trimmed.endswith("_")
            and len(trimmed) >= 2
        ):
            index += 1
            continue
        break
    return "\n".join(lines[index:]).strip()
