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
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        fval = float(val)
        if fval != fval:
            return None
        return int(fval)
    return None


def _get_nested_record(record: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not record:
        return None
    val = record.get(key)
    return val if isinstance(val, dict) else None


def _normalize_surface(value: str | None) -> str | None:
    return value if value == "assistant_message" else None


def _normalize_preferred_height(value: int | float | None) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        fval = float(value)
        if fval != fval:
            return None
        if fval >= 160:
            return min(int(fval), 1200)
    return None


def _scan_fence_spans(buffer: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    offset = 0
    length = len(buffer)
    open_marker_char: str | None = None
    open_marker_len = 0
    open_start = 0
    starts_at_line_start = True

    while offset <= length:
        next_newline = buffer.find("\n", offset)
        line_end = next_newline if next_newline != -1 else length
        line = buffer[offset:line_end]
        if line.endswith("\r"):
            line = line[:-1]

        indent_match = re.match(r"^( {0,3})(`{3,}|~{3,})(.*)$", line)
        if indent_match and (offset > 0 or starts_at_line_start):
            indent = indent_match.group(1)
            marker = indent_match.group(2)
            rest = indent_match.group(3)
            marker_char = marker[0]
            marker_len = len(marker)
            if open_marker_char is None:
                open_marker_char = marker_char
                open_marker_len = marker_len
                open_start = offset
            elif (
                open_marker_char == marker_char
                and marker_len >= open_marker_len
                and re.match(r"^[ \t]*$", rest)
            ):
                spans.append((open_start, line_end))
                open_marker_char = None
                open_marker_len = 0

        if next_newline == -1:
            break
        offset = next_newline + 1

    if open_marker_char is not None:
        spans.append((open_start, length))

    return spans


def coerce_canvas_preview(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    kind = (_get_record_string_field(record, "kind") or "").strip().lower()
    if kind != "canvas":
        return None

    presentation = _get_nested_record(record, "presentation")
    view = _get_nested_record(record, "view")
    source = _get_nested_record(record, "source")

    requested_surface = (
        _get_record_string_field(presentation, "target")
        or _get_record_string_field(record, "target")
    )
    surface = _normalize_surface(requested_surface) if requested_surface else "assistant_message"
    if not surface:
        return None

    title = (
        _get_record_string_field(presentation, "title")
        or _get_record_string_field(view, "title")
    )
    preferred_height = _normalize_preferred_height(
        _get_record_number_field(presentation, "preferred_height")
        or _get_record_number_field(presentation, "preferredHeight")
        or _get_record_number_field(view, "preferred_height")
        or _get_record_number_field(view, "preferredHeight")
    )
    class_name = (
        _get_record_string_field(presentation, "class_name")
        or _get_record_string_field(presentation, "className")
    )
    style = _get_record_string_field(presentation, "style")
    view_url = (
        _get_record_string_field(view, "url")
        or _get_record_string_field(view, "entryUrl")
    )
    view_id = (
        _get_record_string_field(view, "id")
        or _get_record_string_field(view, "docId")
    )

    if view_url:
        preview: dict[str, Any] = {
            "kind": "canvas",
            "surface": surface,
            "render": "url",
            "url": view_url,
        }
        if view_id:
            preview["viewId"] = view_id
        if title:
            preview["title"] = title
        if preferred_height:
            preview["preferredHeight"] = preferred_height
        if class_name:
            preview["className"] = class_name
        if style:
            preview["style"] = style
        return preview

    source_type = (_get_record_string_field(source, "type") or "").strip().lower()
    if source_type == "url":
        url = _get_record_string_field(source, "url")
        if not url:
            return None
        preview = {
            "kind": "canvas",
            "surface": surface,
            "render": "url",
            "url": url,
        }
        if title:
            preview["title"] = title
        if preferred_height:
            preview["preferredHeight"] = preferred_height
        if class_name:
            preview["className"] = class_name
        if style:
            preview["style"] = style
        return preview

    return None


def _parse_canvas_attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    pattern = re.compile(
        r'([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')'
    )
    for match in pattern.finditer(raw):
        key = (match.group(1) or "").strip().lower()
        value = (match.group(2) or match.group(3) or "").strip()
        if key and value:
            attrs[key] = value
    return attrs


def _default_canvas_entry_url(ref: str) -> str:
    encoded = ref.strip()
    from urllib.parse import quote

    encoded = quote(encoded, safe="")
    return f"/__openclaw__/canvas/documents/{encoded}/index.html"


def _preview_from_shortcode(attrs: dict[str, str]) -> dict[str, Any] | None:
    if attrs.get("target") and _normalize_surface(attrs.get("target")) != "assistant_message":
        return None

    surface = "assistant_message"
    title = (attrs.get("title") or "").strip() or None
    preferred_height = None
    if attrs.get("height"):
        try:
            h = float(attrs["height"])
            if h == h:
                preferred_height = _normalize_preferred_height(h)
        except (ValueError, TypeError):
            preferred_height = None
    class_name = (
        (attrs.get("class") or "").strip()
        or (attrs.get("class_name") or "").strip()
        or None
    )
    style = (attrs.get("style") or "").strip() or None
    ref = (attrs.get("ref") or "").strip()
    url = (attrs.get("url") or "").strip()
    if url or ref:
        preview: dict[str, Any] = {
            "kind": "canvas",
            "surface": surface,
            "render": "url",
            "url": url or _default_canvas_entry_url(ref),
        }
        if ref:
            preview["viewId"] = ref
        if title:
            preview["title"] = title
        if preferred_height:
            preview["preferredHeight"] = preferred_height
        if class_name:
            preview["className"] = class_name
        if style:
            preview["style"] = style
        return preview
    return None


def extract_canvas_from_text(
    output_text: str | None,
    _tool_name: str | None = None,
) -> dict[str, Any] | None:
    parsed = _try_parse_json_record(output_text)
    return coerce_canvas_preview(parsed)


def extract_canvas_shortcodes(
    text: str | None,
) -> dict[str, Any]:
    if not text or not text.strip() or "[embed" not in (text or "").lower():
        return {"text": text or "", "previews": []}

    fence_spans = _scan_fence_spans(text)

    matches: list[dict[str, Any]] = []
    block_re = re.compile(
        r"\[embed\s+([^\]]*?[^\]/]|)\]([\s\S]*?)\[\/embed\]", re.IGNORECASE
    )
    self_closing_re = re.compile(
        r"\[embed\s+([^\]]*?)\/\]", re.IGNORECASE
    )
    for regex in (block_re, self_closing_re):
        for m in regex.finditer(text):
            start = m.start()
            in_fence = any(fs <= start < fe for fs, fe in fence_spans)
            if in_fence:
                continue
            groups = m.groups()
            entry: dict[str, Any] = {
                "start": start,
                "end": start + len(m.group(0)),
                "attrs": _parse_canvas_attributes(groups[0] or ""),
                "_has_body": len(groups) >= 2,
            }
            if len(groups) >= 2:
                entry["body"] = groups[1]
            matches.append(entry)

    if not matches:
        return {"text": text, "previews": []}

    matches.sort(key=lambda x: x["start"])
    previews: list[dict[str, Any]] = []
    cursor = 0
    stripped = ""
    for match in matches:
        if match["start"] < cursor:
            continue
        stripped += text[cursor : match["start"]]
        preview = _preview_from_shortcode(match["attrs"])
        if not preview:
            stripped += text[match["start"] : match["end"]]
        else:
            previews.append(preview)
        cursor = match["end"]

    stripped += text[cursor:]
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    return {"text": stripped, "previews": previews}
