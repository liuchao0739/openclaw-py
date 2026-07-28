from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from openclaw_packages.normalization_core import as_optional_record, normalize_optional_string

ToolCallShapedTextKind = Literal[
    "json_tool_call",
    "xml_tool_call",
    "bracketed_tool_call",
    "react_action",
]


@dataclass(frozen=True)
class ToolCallShapedTextDetection:
    kind: ToolCallShapedTextKind
    tool_name: str | None = None


_TOOL_TEXT_PREFILTER_RE = re.compile(
    r"(?:tool[_\s-]?calls?|function[_\s-]?call|[\"'](?:name|tool_name|function|arguments|args|input|parameters|tool_calls)[\"']|<\s*tool_call\b|Action\s*:|\[END_TOOL_REQUEST\])",
    re.IGNORECASE,
)
_MAX_SCAN_CHARS = 20_000
_MAX_JSON_CANDIDATES = 20
_MAX_JSON_CANDIDATE_CHARS = 8_000


def _read_tool_name(record: dict[str, Any]) -> str | None:
    for key in ("name", "tool_name", "tool", "function_name"):
        value = normalize_optional_string(record.get(key))
        if value:
            return value
    return None


def _has_tool_args(record: dict[str, Any]) -> bool:
    return any(k in record for k in ("arguments", "args", "input", "parameters"))


def _classify_json_value(value: Any) -> ToolCallShapedTextDetection | None:
    if isinstance(value, list):
        for item in value:
            detection = _classify_json_value(item)
            if detection:
                return detection
        return None

    record = as_optional_record(value)
    if not record:
        return None

    tool_calls = record.get("tool_calls") or record.get("toolCalls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            detection = _classify_json_value(tool_call)
            if detection:
                return detection
        return ToolCallShapedTextDetection(kind="json_tool_call")

    function_record = as_optional_record(record.get("function"))
    if function_record:
        tool_name = _read_tool_name(function_record)
        if tool_name and _has_tool_args(function_record):
            return ToolCallShapedTextDetection(kind="json_tool_call", tool_name=tool_name)

    tool_name = _read_tool_name(record)
    if tool_name and _has_tool_args(record):
        return ToolCallShapedTextDetection(kind="json_tool_call", tool_name=tool_name)

    type_value = normalize_optional_string(record.get("type"))
    if tool_name and type_value:
        type_lower = type_value.lower()
        if type_lower in (
            "tool_call",
            "toolcall",
            "tooluse",
            "tool_use",
            "function_call",
            "functioncall",
        ):
            return ToolCallShapedTextDetection(kind="json_tool_call", tool_name=tool_name)

    return None


_FENCE_RE = re.compile(
    r"```(?:json|tool|tool_call|function_call)?[^\n\r]*[\r\n]([\s\S]*?)```",
    re.IGNORECASE,
)


def _collect_fenced_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for match in _FENCE_RE.finditer(text):
        candidate = match.group(1).strip() if match.group(1) else ""
        if candidate and len(candidate) <= _MAX_JSON_CANDIDATE_CHARS:
            candidates.append(candidate)
    return candidates


def _find_balanced_json_end(text: str, start: int) -> int | None:
    opening = text[start]
    closing = "}" if opening == "{" else "]" if opening == "[" else ""
    if not closing:
        return None

    stack = [closing]
    in_string = False
    escaped = False
    for index in range(start + 1, len(text)):
        if index - start > _MAX_JSON_CANDIDATE_CHARS:
            return None
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
            continue
        if ch in ("}", "]"):
            if stack[-1] != ch:
                return None
            stack.pop()
            if not stack:
                return index + 1
    return None


def _collect_balanced_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    index = 0
    while index < len(text) and len(candidates) < _MAX_JSON_CANDIDATES:
        ch = text[index]
        if ch not in ("{", "["):
            index += 1
            continue
        end = _find_balanced_json_end(text, index)
        if end is None:
            index += 1
            continue
        candidate = text[index:end].strip()
        if len(candidate) > 1:
            candidates.append(candidate)
        index = end - 1
    return candidates


def _detect_json_tool_call(text: str) -> ToolCallShapedTextDetection | None:
    candidates = _collect_fenced_json_candidates(text) + _collect_balanced_json_candidates(
        text
    )
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (ValueError, json.JSONDecodeError):
            continue
        detection = _classify_json_value(parsed)
        if detection:
            return detection
    return None


_XML_TAG_RE = re.compile(r"<\s*tool_call\b", re.IGNORECASE)
_XML_FUNCTION_RE = re.compile(r"<\s*function=([A-Za-z0-9_.:-]{1,120})\b", re.IGNORECASE)
_XML_NAME_RE = re.compile(r"[\"']name[\"']\s*:\s*[\"']([^\"']{1,120})[\"']", re.IGNORECASE)
_XML_ATTR_RE = re.compile(r"<\s*function=", re.IGNORECASE)


def _detect_xml_tool_call(text: str) -> ToolCallShapedTextDetection | None:
    if not _XML_TAG_RE.search(text):
        return None
    if not _XML_ATTR_RE.search(text):
        name_match = _XML_NAME_RE.search(text)
        if not name_match:
            return None
    tool_name = None
    function_match = _XML_FUNCTION_RE.search(text)
    if function_match:
        tool_name = function_match.group(1)
    else:
        name_match = _XML_NAME_RE.search(text)
        if name_match:
            tool_name = name_match.group(1).strip()
    return ToolCallShapedTextDetection(
        kind="xml_tool_call", tool_name=tool_name
    )


_LEGACY_BRACKET_RE = re.compile(
    r"\[\s*TOOL_CALL\s*\]\s*\{[\s\S]{0,8000}?\btool\s*=>\s*[\"']([A-Za-z_][A-Za-z0-9_.:-]{0,119})[\"'][\s\S]{0,8000}?\bargs\s*=>[\s\S]*?(?:\[\s*\/\s*TOOL_CALL\s*\]|$)",
    re.IGNORECASE,
)
_END_TOOL_REQUEST_RE = re.compile(
    r"^\s*\[([A-Za-z_][A-Za-z0-9_.:-]{0,119})\]\s+[\s\S]*?\[END_TOOL_REQUEST\]\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _detect_bracketed_tool_call(text: str) -> ToolCallShapedTextDetection | None:
    legacy_match = _LEGACY_BRACKET_RE.search(text)
    if legacy_match and legacy_match.group(1):
        return ToolCallShapedTextDetection(
            kind="bracketed_tool_call", tool_name=legacy_match.group(1)
        )

    match = _END_TOOL_REQUEST_RE.search(text)
    if not match or not match.group(1):
        return None
    return ToolCallShapedTextDetection(
        kind="bracketed_tool_call", tool_name=match.group(1)
    )


_REACT_ACTION_RE = re.compile(
    r"(?:^|\n)\s*Action\s*:\s*([A-Za-z_][A-Za-z0-9_.:-]{0,119})\s*(?:\r?\n)+\s*Action Input\s*:",
    re.IGNORECASE,
)


def _detect_react_action(text: str) -> ToolCallShapedTextDetection | None:
    match = _REACT_ACTION_RE.search(text)
    if not match or not match.group(1):
        return None
    return ToolCallShapedTextDetection(kind="react_action", tool_name=match.group(1))


def detect_tool_call_shaped_text(text: str) -> ToolCallShapedTextDetection | None:
    trimmed = text[:_MAX_SCAN_CHARS].strip()
    if not trimmed or not _TOOL_TEXT_PREFILTER_RE.search(trimmed):
        return None
    return (
        _detect_bracketed_tool_call(trimmed)
        or _detect_xml_tool_call(trimmed)
        or _detect_json_tool_call(trimmed)
        or _detect_react_action(trimmed)
    )
