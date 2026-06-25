"""Minimal HTML entity decoding helpers.

Decodes the small entity subset emitted by trusted HTML producers without
parsing full HTML.
"""

from __future__ import annotations

from typing import Any

_NAMED_ENTITIES = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
}


def _decode_code_point(code_point: int) -> str | None:
    if not isinstance(code_point, int) or code_point < 0 or code_point > 0x10FFFF:
        return None
    try:
        return chr(code_point)
    except (ValueError, OverflowError):
        return None


def _decode_html_entity(entity: str) -> str | None:
    """Decode a named or numeric HTML entity without the surrounding &/;."""
    if entity in _NAMED_ENTITIES:
        return _NAMED_ENTITIES[entity]

    if entity.startswith("#x") or entity.startswith("#X"):
        try:
            return _decode_code_point(int(entity[2:], 16))
        except ValueError:
            return None

    if entity.startswith("#"):
        try:
            return _decode_code_point(int(entity[1:], 10))
        except ValueError:
            return None

    return None


def decode_html_entity_at(html: str, index: int) -> dict[str, Any] | None:
    """Decode an entity starting at ``index`` in an HTML string."""
    semicolon_index = html.find(";", index + 1)
    if semicolon_index == -1 or semicolon_index - index > 16:
        return None

    entity = html[index + 1:semicolon_index]
    decoded = _decode_html_entity(entity)
    if decoded is None:
        return None

    return {"text": decoded, "length": semicolon_index - index + 1}


def decode_html_entities(html: str) -> str:
    """Decode all HTML entities in a string."""
    result: list[str] = []
    i = 0
    while i < len(html):
        if html[i] == "&":
            decoded = decode_html_entity_at(html, i)
            if decoded is not None:
                result.append(decoded["text"])
                i += decoded["length"]
                continue
        result.append(html[i])
        i += 1
    return "".join(result)
