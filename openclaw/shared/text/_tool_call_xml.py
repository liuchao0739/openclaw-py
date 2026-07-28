from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty

from .code_regions import find_code_regions, is_inside_code

ToolCallPayloadKind = Literal["json", "xml", "null"]

_TOOL_CALL_QUICK_RE = re.compile(
    r"<\s*\/?\s*(?:tool_call|tool_result|function_calls?|function_response|function|tool_calls)\b",
    re.IGNORECASE,
)
_TOOL_CALL_TAG_NAMES = frozenset(
    (
        "tool_call",
        "tool_result",
        "function_call",
        "function_calls",
        "function_response",
        "function",
        "tool_calls",
    )
)
_TOOL_CALL_JSON_PAYLOAD_START_RE = re.compile(
    r"^(?:\s+[A-Za-z_:][-A-Za-z0-9_:.]*\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))*\s*(?:\r?\n\s*)?[\[{]"
)
_TOOL_CALL_XML_PAYLOAD_START_RE = re.compile(
    r"^\s*(?:\r?\n\s*)?<(?:function_call|tool_call|function|invoke|parameters?|arguments?)\b",
    re.IGNORECASE,
)
_NESTED_JSON_TOOL_CALL_PAYLOAD_START_RE = re.compile(
    r"^\s*(?:\r?\n\s*)?<(?:function_call|tool_call)\b", re.IGNORECASE
)


@dataclass
class _ParsedToolCallTag:
    content_start: int
    end: int
    is_close: bool
    is_self_closing: bool
    tag_name: str
    is_truncated: bool


def _ends_inside_quoted_string(text: str, start: int, end: int) -> bool:
    quote_char: str | None = None
    is_escaped = False

    for idx in range(start, end):
        char = text[idx]
        if quote_char is None:
            if char in ('"', "'"):
                quote_char = char
            continue

        if is_escaped:
            is_escaped = False
            continue

        if char == "\\":
            is_escaped = True
            continue

        if char == quote_char:
            quote_char = None

    return quote_char is not None


def _is_tool_call_boundary(char: str | None) -> bool:
    if char is None:
        return True
    return char.isspace() or char in ("/", ">")


def _find_tag_close_index(text: str, start: int) -> int:
    quote_char: str | None = None
    is_escaped = False

    idx = start
    while idx < len(text):
        char = text[idx]
        if quote_char is not None:
            if is_escaped:
                is_escaped = False
                idx += 1
                continue
            if char == "\\":
                is_escaped = True
                idx += 1
                continue
            if char == quote_char:
                quote_char = None
            idx += 1
            continue

        if char in ('"', "'"):
            quote_char = char
            idx += 1
            continue
        if char == "<":
            return -1
        if char == ">":
            return idx
        idx += 1

    return -1


def _detect_tool_call_payload_kind(text: str, start: int) -> ToolCallPayloadKind:
    rest = text[start:]
    if _TOOL_CALL_JSON_PAYLOAD_START_RE.match(rest):
        return "json"
    if _TOOL_CALL_XML_PAYLOAD_START_RE.match(rest):
        return "xml"
    return "null"


def _starts_with_nested_json_tool_call_payload(text: str, start: int) -> bool:
    if not _NESTED_JSON_TOOL_CALL_PAYLOAD_START_RE.match(text[start:]):
        return False
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    nested_tag = _parse_tool_call_tag_at(text, cursor)
    if (
        nested_tag is None
        or nested_tag.is_close
        or nested_tag.is_self_closing
        or nested_tag.is_truncated
        or nested_tag.tag_name not in ("function_call", "tool_call")
    ):
        return False
    return bool(
        _TOOL_CALL_JSON_PAYLOAD_START_RE.match(text[nested_tag.end:])
    )


def _is_likely_standalone_function_tool_call(
    text: str,
    tag_start: int,
    tag: _ParsedToolCallTag,
) -> bool:
    if tag.tag_name != "function" or tag.is_close or tag.is_self_closing or tag.is_truncated:
        return False

    if not re.search(r"\bname\s*=", text[tag.content_start : tag.end]):
        return False

    idx = tag_start - 1
    while idx >= 0 and text[idx] in (" ", "\t"):
        idx -= 1

    return idx < 0 or text[idx] in ("\n", "\r") or text[idx] in (".", "!", "?", ":")


def _is_standalone_opening_tag_line(
    text: str,
    tag_start: int,
    tag: _ParsedToolCallTag,
) -> bool:
    idx = tag_start - 1
    while idx >= 0 and text[idx] in (" ", "\t"):
        idx -= 1
    if not (idx < 0 or text[idx] in ("\n", "\r")):
        return False
    after = tag.end
    while after < len(text) and text[after] in (" ", "\t"):
        after += 1
    return after >= len(text) or text[after] in ("\n", "\r")


def _is_opening_tag_followed_by_line_break(
    text: str, tag: _ParsedToolCallTag
) -> bool:
    after = tag.end
    while after < len(text) and text[after] in (" ", "\t"):
        after += 1
    return after >= len(text) or text[after] in ("\n", "\r")


def _has_same_line_content_after_opening_tag(
    text: str, tag: _ParsedToolCallTag
) -> bool:
    after = tag.end
    while after < len(text) and text[after] in (" ", "\t"):
        after += 1
    return after < len(text) and text[after] not in ("\n", "\r")


def _is_visible_line_start(text: str) -> bool:
    idx = len(text) - 1
    while idx >= 0 and text[idx] in (" ", "\t"):
        idx -= 1
    return idx < 0 or text[idx] in ("\n", "\r")


def _is_adjacent_to_stripped_tool_call_block(
    text: str,
    tag_start: int,
    last_stripped_block_end: int | None,
) -> bool:
    if last_stripped_block_end is None or last_stripped_block_end > tag_start:
        return False
    for idx in range(last_stripped_block_end, tag_start):
        if text[idx] not in (" ", "\t", "\n", "\r"):
            return False
    return True


def _find_matching_tool_call_close_index(
    text: str, start: int, tag_name: str
) -> int:
    idx = start
    while idx < len(text):
        if text[idx] != "<":
            idx += 1
            continue
        tag = _parse_tool_call_tag_at(text, idx)
        if tag is None:
            idx += 1
            continue
        if tag.is_close and tag.tag_name == tag_name and not tag.is_truncated:
            return idx
        idx = max(idx, tag.end - 1)
    return -1


def _find_adjacent_opening_tool_call_tag(
    text: str, start: int, tag_name: str
) -> _ParsedToolCallTag | None:
    idx = start
    while idx < len(text) and text[idx].isspace():
        idx += 1
    if idx >= len(text) or text[idx] != "<":
        return None
    tag = _parse_tool_call_tag_at(text, idx)
    if tag is None or tag.is_close or tag.tag_name != tag_name:
        return None
    return tag


def _parse_tool_call_tag_at(text: str, start: int) -> _ParsedToolCallTag | None:
    if text[start] != "<":
        return None

    cursor = start + 1
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1

    is_close = False
    if cursor < len(text) and text[cursor] == "/":
        is_close = True
        cursor += 1
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1

    name_start = cursor
    while cursor < len(text) and (text[cursor].isalpha() or text[cursor] == "_"):
        cursor += 1

    tag_name = normalize_lowercase_string_or_empty(text[name_start:cursor])
    if tag_name not in _TOOL_CALL_TAG_NAMES or not _is_tool_call_boundary(
        text[cursor] if cursor < len(text) else None
    ):
        return None
    content_start = cursor

    close_index = _find_tag_close_index(text, cursor)
    if close_index == -1:
        return _ParsedToolCallTag(
            content_start=content_start,
            end=len(text),
            is_close=is_close,
            is_self_closing=False,
            tag_name=tag_name,
            is_truncated=True,
        )

    slice_between = text[cursor:close_index]
    is_self_closing = (not is_close) and bool(re.search(r"/\s*$", slice_between))
    return _ParsedToolCallTag(
        content_start=content_start,
        end=close_index + 1,
        is_close=is_close,
        is_self_closing=is_self_closing,
        tag_name=tag_name,
        is_truncated=False,
    )


def strip_tool_call_xml_tags(
    text: str,
    strip_function_calls_xml_payloads: bool = False,
    strip_function_response_after_plural_tool_calls: bool = False,
) -> str:
    if not text or not _TOOL_CALL_QUICK_RE.search(text):
        return text

    code_regions = find_code_regions(text)
    result: list[str] = []
    last_index = 0
    in_tool_call_block = False
    tool_call_block_content_start = 0
    tool_call_block_needs_quote_balance = False
    tool_call_block_start = 0
    tool_call_block_tag_name: str | None = None
    last_stripped_tool_call_block_end: int | None = None
    visible_tag_balance: dict[str, int] = {}

    idx = 0
    while idx < len(text):
        if text[idx] != "<":
            idx += 1
            continue
        if not in_tool_call_block and is_inside_code(idx, code_regions):
            idx += 1
            continue

        tag = _parse_tool_call_tag_at(text, idx)
        if tag is None:
            idx += 1
            continue

        if not in_tool_call_block:
            result.append(text[last_index:idx])
            if tag.is_close:
                if tag.is_truncated:
                    preserve_end = tag.content_start
                    result.append(text[idx:preserve_end])
                    last_index = preserve_end
                    idx = max(idx, preserve_end - 1)
                    continue
                balance = visible_tag_balance.get(tag.tag_name, 0)
                if balance > 0:
                    result.append(text[idx : tag.end])
                    visible_tag_balance[tag.tag_name] = balance - 1
                last_index = tag.end
                idx = max(idx, tag.end - 1)
                continue
            if tag.is_self_closing:
                last_stripped_tool_call_block_end = tag.end
                last_index = tag.end
                idx = max(idx, tag.end - 1)
                continue
            payload_start = tag.content_start if tag.is_truncated else tag.end
            is_plural_tool_call_wrapper = tag.tag_name in ("function_calls", "tool_calls")
            matching_close_start = (
                _find_matching_tool_call_close_index(text, tag.end, tag.tag_name)
                if is_plural_tool_call_wrapper
                else -1
            )
            matching_close_tag = (
                _parse_tool_call_tag_at(text, matching_close_start)
                if matching_close_start != -1
                else None
            )
            should_strip_plural_wrapper_before_response = (
                strip_function_response_after_plural_tool_calls
                and is_plural_tool_call_wrapper
                and matching_close_tag is not None
                and _find_adjacent_opening_tool_call_tag(
                    text, matching_close_tag.end, "function_response"
                )
                is not None
            )
            should_detect_xml_payload = (
                tag.tag_name in ("tool_call", "function")
                or (
                    (
                        strip_function_calls_xml_payloads
                        or should_strip_plural_wrapper_before_response
                    )
                    and is_plural_tool_call_wrapper
                )
            )
            payload_kind = (
                _detect_tool_call_payload_kind(text, payload_start)
                if should_detect_xml_payload
                else (
                    "json"
                    if _TOOL_CALL_JSON_PAYLOAD_START_RE.match(text[payload_start:])
                    else "null"
                )
            )
            should_strip_standalone_function = tag.tag_name != "function" or _is_likely_standalone_function_tool_call(
                text, idx, tag
            )
            function_response_close_start = (
                _find_matching_tool_call_close_index(text, tag.end, tag.tag_name)
                if tag.tag_name == "function_response"
                else -1
            )
            should_strip_adjacent_result = (
                _is_adjacent_to_stripped_tool_call_block(
                    text, idx, last_stripped_tool_call_block_end
                )
                and (
                    _is_opening_tag_followed_by_line_break(text, tag)
                    or function_response_close_start != -1
                    or _has_same_line_content_after_opening_tag(text, tag)
                )
            )
            should_strip_standalone_result = (
                tag.tag_name == "function_response"
                and (
                    _is_standalone_opening_tag_line(text, idx, tag)
                    or should_strip_adjacent_result
                    or (
                        function_response_close_start != -1
                        and _is_visible_line_start("".join(result))
                        and _is_opening_tag_followed_by_line_break(text, tag)
                    )
                )
            )
            if (
                not tag.is_close
                and (
                    (payload_kind != "null" and should_strip_standalone_function)
                    or should_strip_standalone_result
                )
            ):
                in_tool_call_block = True
                tool_call_block_content_start = tag.end
                tool_call_block_needs_quote_balance = (
                    payload_kind == "json"
                    or (
                        payload_kind == "xml"
                        and _starts_with_nested_json_tool_call_payload(
                            text, payload_start
                        )
                    )
                )
                tool_call_block_start = idx
                tool_call_block_tag_name = tag.tag_name
                if tag.is_truncated:
                    last_index = len(text)
                    idx = len(text)
                    break
            else:
                preserve_end = tag.content_start if tag.is_truncated else tag.end
                result.append(text[idx:preserve_end])
                if not tag.is_truncated:
                    visible_tag_balance[tag.tag_name] = (
                        visible_tag_balance.get(tag.tag_name, 0) + 1
                    )
                last_index = preserve_end
                idx = max(idx, preserve_end - 1)
                continue
        elif tag.is_close and (
            tag.tag_name == tool_call_block_tag_name
            or (
                tool_call_block_tag_name == "tool_result"
                and tag.tag_name == "tool_call"
            )
        ) and (
            not tool_call_block_needs_quote_balance
            or not _ends_inside_quoted_string(
                text, tool_call_block_content_start, idx
            )
        ):
            closed_block_tag_name = tool_call_block_tag_name
            in_tool_call_block = False
            tool_call_block_needs_quote_balance = False
            tool_call_block_tag_name = None
            if closed_block_tag_name:
                last_stripped_tool_call_block_end = tag.end

        last_index = tag.end
        idx = max(idx, tag.end - 1)

    if not in_tool_call_block:
        result.append(text[last_index:])
    elif tool_call_block_tag_name == "function":
        result.append(text[tool_call_block_start:])

    return "".join(result)


_MINIMAX_TOOL_XML_RE = re.compile(
    r"<invoke\b[^>]*>[\s\S]*?<\/invoke>|<\/?minimax:tool_call>",
    re.IGNORECASE,
)


def strip_minimax_tool_call_xml(text: str) -> str:
    if not text or not re.search(r"minimax:tool_call", text, re.IGNORECASE):
        return text

    code_regions = find_code_regions(text)
    result: list[str] = []
    cursor = 0
    for match in _MINIMAX_TOOL_XML_RE.finditer(text):
        start = match.start()
        if is_inside_code(start, code_regions):
            continue
        result.append(text[cursor:start])
        cursor = start + len(match.group(0))
    result.append(text[cursor:])
    return "".join(result)


_LEGACY_BRACKET_TOOL_BLOCK_QUICK_RE = re.compile(
    r"\[\s*\/?\s*TOOL_(?:CALL|RESULT)\s*\]",
    re.IGNORECASE,
)


def _is_legacy_bracket_tool_call_payload(value: str) -> bool:
    return bool(
        re.search(
            r"\btool\s*=>\s*[\"'][A-Za-z_][A-Za-z0-9_.:-]{0,119}[\"']",
            value,
            re.IGNORECASE,
        )
        and re.search(r"\bargs\s*=>", value, re.IGNORECASE)
    )


def _is_legacy_bracket_tool_result_payload(value: str) -> bool:
    return bool(
        re.match(r"\s*[{[]", value)
        or re.search(
            r"\b(?:tool|result|output|content)\s*=>", value, re.IGNORECASE
        )
        or re.search(
            r"\b(?:tool|result|output|content)\s*:", value, re.IGNORECASE
        )
    )


def strip_legacy_bracket_tool_call_blocks(text: str) -> str:
    if not text or not _LEGACY_BRACKET_TOOL_BLOCK_QUICK_RE.search(text):
        return text

    code_regions = find_code_regions(text)
    result: list[str] = []
    cursor = 0
    while cursor < len(text):
        slice_text = text[cursor:]
        open_match = re.search(
            r"\[\s*TOOL_(CALL|RESULT)\s*\]", slice_text, re.IGNORECASE
        )
        if not open_match:
            result.append(text[cursor:])
            break
        block_kind = open_match.group(1).upper()
        open_start = cursor + open_match.start()
        payload_start = open_start + len(open_match.group(0))
        if is_inside_code(open_start, code_regions):
            result.append(text[cursor:payload_start])
            cursor = payload_start
            continue

        close_re = (
            re.compile(r"\[\s*\/\s*TOOL_RESULT\s*\]", re.IGNORECASE)
            if block_kind == "RESULT"
            else re.compile(r"\[\s*\/\s*TOOL_CALL\s*\]", re.IGNORECASE)
        )
        close_match = close_re.search(text[payload_start:])
        close_start = (
            payload_start + close_match.start()
            if close_match
            and not is_inside_code(
                payload_start + close_match.start(), code_regions
            )
            else -1
        )
        payload_end = close_start if close_start >= 0 else len(text)
        payload = text[payload_start:payload_end]
        should_strip = (
            _is_legacy_bracket_tool_result_payload(payload)
            if block_kind == "RESULT"
            else _is_legacy_bracket_tool_call_payload(payload)
        )
        if not should_strip:
            result.append(text[cursor:payload_start])
            cursor = payload_start
            continue

        result.append(text[cursor:open_start])
        cursor = (
            close_start + len(close_match.group(0))
            if close_start >= 0 and close_match
            else len(text)
        )

    return "".join(result)
