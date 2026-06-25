"""Renders chat canvas payloads into text and metadata for transcript output."""

from __future__ import annotations

import json
import re
from typing import Any


def _try_parse_json_record(value: str | None) -> dict[str, Any] | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _get_record_string_field(record: dict[str, Any] | None, key: str) -> str | None:
    if not record:
        return None
    val = record.get(key)
    if isinstance(val, str) and val.strip():
        return val
    return None


def _get_record_number_field(record: dict[str, Any] | None, key: str) -> int | None:
    if not record:
        return None
    val = record.get(key)
    if isinstance(val, (int, float)) and val == val:  # not NaN
        return int(val)
    return None


def _get_nested_record(record: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not record:
        return None
    val = record.get(key)
    return val if isinstance(val, dict) else None


def _normalize_preferred_height(value: int | None) -> int | None:
    if value is not None and isinstance(value, (int, float)) and value >= 160:
        return min(int(value), 1200)
    return None


def coerce_canvas_preview(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Coerce a JSON record into a canvas preview if it matches the expected shape."""
    if not record:
        return None
    kind = (_get_record_string_field(record, "kind") or "").strip().lower()
    if kind != "canvas":
        return None

    presentation = _get_nested_record(record, "presentation")
    view = _get_nested_record(record, "view")
    source = _get_nested_record(record, "source")

    surface = _get_record_string_field(presentation, "target") or _get_record_string_field(record, "surface")
    if surface != "assistant_message":
        return None

    preview: dict[str, Any] = {
        "kind": "canvas",
        "surface": "assistant_message",
        "render": "url",
    }

    title = _get_record_string_field(view, "title") or _get_record_string_field(record, "title")
    if title:
        preview["title"] = title

    height = _normalize_preferred_height(
        _get_record_number_field(presentation, "preferredHeight")
        or _get_record_number_field(record, "preferredHeight")
    )
    if height:
        preview["preferredHeight"] = height

    url = _get_record_string_field(source, "url") or _get_record_string_field(record, "url")
    if url:
        preview["url"] = url

    view_id = _get_record_string_field(view, "id") or _get_record_string_field(record, "viewId")
    if view_id:
        preview["viewId"] = view_id

    return preview


_SHORTCODE_PATTERN = re.compile(r"\[canvas(?::([^\]]+))?\]", re.IGNORECASE)


def extract_canvas_previews(text: str) -> dict[str, Any]:
    """Extract canvas previews from text, returning stripped text and preview list."""
    previews: list[dict[str, Any]] = []
    stripped = ""
    cursor = 0

    for match in _SHORTCODE_PATTERN.finditer(text):
        stripped += text[cursor:match.start()]
        attrs_str = match.group(1) or ""

        # Parse shortcode attributes
        record: dict[str, Any] = {"kind": "canvas", "surface": "assistant_message"}
        for attr in attrs_str.split():
            if "=" in attr:
                key, _, val = attr.partition("=")
                record[key.strip()] = val.strip().strip('"').strip("'")

        preview = coerce_canvas_preview(record)
        if preview:
            previews.append(preview)
        else:
            stripped += text[match.start():match.end()]

        cursor = match.end()

    stripped += text[cursor:]
    # Collapse excessive newlines
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()

    return {"text": stripped, "previews": previews}
