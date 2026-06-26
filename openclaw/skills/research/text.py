"""Research text helpers extract text blocks from model messages for skill
research capture.

Mirrors src/skills/research/text.ts.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_TEXT_BLOCK_TYPES = frozenset({"text", "input_text", "output_text"})


def _read_text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping) and isinstance(value.get("value"), str):
        return value["value"]
    return ""


def _extract_text_block(block: Any) -> str:
    if not isinstance(block, Mapping):
        return ""
    block_type = block.get("type")
    if not isinstance(block_type, str) or block_type not in _TEXT_BLOCK_TYPES:
        return ""
    return _read_text_value(block.get("text"))


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(text for text in (_extract_text_block(b) for b in content) if text)
    return _extract_text_block(content)


def extract_transcript_text(
    messages: list[Any],
) -> list[dict[str, str]]:
    """Extract role/text pairs from mixed transcript message shapes."""
    result: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str):
            continue
        text = _extract_message_text(content).strip()
        if text:
            result.append({"role": role, "text": text})
    return result


def compact_whitespace(value: str) -> str:
    """Compact multiple whitespace characters into single spaces."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()
