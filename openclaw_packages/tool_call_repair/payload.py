import json
import re
from dataclasses import dataclass, field
from typing import Optional, Set

from .grammar import (
    END_TOOL_REQUEST,
    HARMONY_CALL_MARKER,
    HARMONY_CHANNEL_MARKER,
    HARMONY_MESSAGE_MARKER,
    consume_line_break,
    find_json_object_end,
    is_plain_text_tool_name_char,
    skip_horizontal_whitespace,
    skip_whitespace,
)


@dataclass
class PlainTextToolCallBlock:
    arguments: dict = field(default_factory=dict)
    end: int = 0
    name: str = ""
    raw: str = ""
    start: int = 0


@dataclass
class PlainTextToolCallParseOptions:
    allowed_tool_names: Optional[Set[str]] = None
    max_payload_bytes: Optional[int] = None


DEFAULT_MAX_PLAIN_TEXT_TOOL_PAYLOAD_BYTES = 256000


@dataclass
class _Opening:
    allows_optional_xmlish_close: bool = False
    end: int = 0
    name: str = ""
    requires_closing: bool = False


@dataclass
class _XmlishBounds:
    close_start: int = 0
    end: int = 0
    name: str = ""
    payload_start: int = 0
    start: int = 0


def _parse_bracket_opening(text: str, start: int) -> Optional[_Opening]:
    if text[start] != "[":
        return None
    cursor = start + 1
    if text.startswith("tool:", cursor):
        cursor += len("tool:")
        name_start = cursor
        while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
            cursor += 1
        if cursor == name_start or cursor >= len(text) or text[cursor] != "]":
            return None
        return _Opening(True, cursor + 1, text[name_start:cursor], False)
    name_start = cursor
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    if cursor == name_start or cursor >= len(text) or text[cursor] != "]":
        return None
    name = text[name_start:cursor]
    cursor += 1
    cursor = skip_horizontal_whitespace(text, cursor)
    after_lb = consume_line_break(text, cursor)
    if after_lb is None:
        return None
    return _Opening(False, after_lb, name, True)


def _parse_harmony_opening(text: str, start: int) -> Optional[_Opening]:
    cursor = start
    if text.startswith(HARMONY_CHANNEL_MARKER, cursor):
        cursor += len(HARMONY_CHANNEL_MARKER)
    ch_start = cursor
    while cursor < len(text) and re.match(r"[A-Za-z_]", text[cursor] or ""):
        cursor += 1
    channel = text[ch_start:cursor]
    if channel not in ("commentary", "analysis", "final"):
        return None
    cursor = skip_horizontal_whitespace(text, cursor)
    if not text.startswith("to=", cursor):
        return None
    cursor += 3
    name_start = cursor
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    if cursor == name_start:
        return None
    name = text[name_start:cursor]
    cursor = skip_horizontal_whitespace(text, cursor)
    if not text.startswith("code", cursor):
        return None
    cursor += 4
    cursor = skip_whitespace(text, cursor)
    if text.startswith(HARMONY_MESSAGE_MARKER, cursor):
        cursor = skip_whitespace(text, cursor + len(HARMONY_MESSAGE_MARKER))
    return _Opening(False, cursor, name, False)


def _parse_xmlish_function_opening(text: str, start: int) -> Optional[_Opening]:
    m = re.match(r"^<function=([A-Za-z0-9_.:-]{1,120})>\s*", text[start:], re.IGNORECASE)
    if not m or not m.group(1):
        return None
    return _Opening(False, start + len(m.group(0)), m.group(1), False)


def _parse_opening(text: str, start: int) -> Optional[_Opening]:
    r = _parse_bracket_opening(text, start)
    if r is not None:
        return r
    return _parse_harmony_opening(text, start)


def _consume_json(text: str, start: int, max_payload: int) -> Optional[tuple]:
    cursor = skip_whitespace(text, start)
    if cursor >= len(text) or text[cursor] != "{":
        return None
    end = find_json_object_end(text, cursor, max_payload)
    if end is None:
        return None
    raw = text[cursor:end]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not parsed or not isinstance(parsed, dict):
        return None
    return end, parsed


def _parse_closing(text: str, start: int, name: str) -> Optional[int]:
    cursor = skip_whitespace(text, start)
    if text.startswith(END_TOOL_REQUEST, cursor):
        return cursor + len(END_TOOL_REQUEST)
    nc = f"[/{name}]"
    if text.startswith(nc, cursor):
        return cursor + len(nc)
    return None


def _parse_optional_harmony_closing(text: str, start: int) -> int:
    cursor = skip_whitespace(text, start)
    if text.startswith(HARMONY_CALL_MARKER, cursor):
        return cursor + len(HARMONY_CALL_MARKER)
    return start


def _parse_block_at(
    text: str,
    start: int,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> Optional[PlainTextToolCallBlock]:
    opening = _parse_opening(text, start)
    if opening is None:
        return None
    allowed = opts.allowed_tool_names if opts else None
    if allowed and opening.name not in allowed:
        return None
    max_pl = opts.max_payload_bytes if opts else None
    if max_pl is None:
        max_pl = DEFAULT_MAX_PLAIN_TEXT_TOOL_PAYLOAD_BYTES
    payload = _consume_json(text, opening.end, max_pl)
    if payload is None:
        return None
    pend, val = payload
    if opening.requires_closing:
        cend = _parse_closing(text, pend, opening.name)
    else:
        cend = _parse_optional_harmony_closing(text, pend)
    if cend is None:
        return None
    return PlainTextToolCallBlock(val, cend, opening.name, text[start:cend], start)


def _find_xmlish_param(text: str, start: int) -> Optional[_XmlishBounds]:
    cursor = skip_horizontal_whitespace(text, start)
    om = re.match(r"^<parameter=([A-Za-z0-9_.:-]{1,120})>", text[cursor:], re.IGNORECASE)
    if not om or not om.group(1):
        return None
    ps = cursor + len(om.group(0))
    cm = re.search(r"<\/parameter>", text[ps:], re.IGNORECASE)
    if not cm:
        return None
    close_start = ps + cm.start()
    end = close_start + len("<\/parameter>")
    return _XmlishBounds(
        close_start=close_start,
        end=end,
        name=om.group(1),
        payload_start=ps,
        start=cursor,
    )


def _extract_xmlish_function_blocks(text: str, start: int, end: int) -> list:
    blocks = []
    cursor = start
    while cursor < end:
        opening = _parse_xmlish_function_opening(text, cursor)
        if opening is None:
            cursor += 1
            continue
        if opening.end > end:
            break
        args = {}
        pstart = opening.end
        while pstart < end:
            pb = _find_xmlish_param(text, pstart)
            if pb is None or pb.start >= end:
                break
            if pb.end > end:
                break
            val = None
            try:
                val = json.loads(text[pb.payload_start:pb.close_start])
            except json.JSONDecodeError:
                pass
            if val is not None:
                args[pb.name] = val
            pstart = pb.end
        raw_end = pstart
        blocks.append(PlainTextToolCallBlock(args, raw_end, opening.name, text[cursor:raw_end], cursor))
        cursor = raw_end
    return blocks


def _strip_xmlish_function_blocks(text: str, start: int, end: int) -> str:
    blocks = _extract_xmlish_function_blocks(text, start, end)
    if not blocks:
        return text[start:end]
    parts = []
    cursor = start
    for block in blocks:
        if block.start > cursor:
            parts.append(text[cursor:block.start])
        cursor = block.end
    if cursor < end:
        parts.append(text[cursor:end])
    return "".join(parts)


def parse_standalone_plain_text_tool_call_blocks(
    text: str,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> Optional[list]:
    return find_plain_text_tool_call_blocks_in_range(text, 0, len(text), opts)


def find_plain_text_tool_call_blocks(
    text: str,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> list:
    return find_plain_text_tool_call_blocks_in_range(text, 0, len(text), opts)


def find_plain_text_tool_call_blocks_in_range(
    text: str,
    start: int,
    end: int,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> list:
    blocks = []
    cursor = start
    while cursor < end:
        block = _parse_block_at(text, cursor, opts)
        if block is not None:
            blocks.append(block)
            cursor = block.end
        else:
            cursor += 1
    blocks.extend(_extract_xmlish_function_blocks(text, start, end))
    blocks.sort(key=lambda b: b.start)
    return blocks


def strip_plain_text_tool_call_blocks(
    text: str,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> str:
    return strip_plain_text_tool_call_blocks_in_range(text, 0, len(text), opts)


def strip_plain_text_tool_call_blocks_in_range(
    text: str,
    start: int,
    end: int,
    opts: Optional[PlainTextToolCallParseOptions] = None,
) -> str:
    blocks = find_plain_text_tool_call_blocks_in_range(text, start, end, opts)
    if not blocks:
        return text[start:end]
    parts = []
    cursor = start
    for block in blocks:
        if block.start > cursor:
            parts.append(text[cursor:block.start])
        cursor = block.end
    if cursor < end:
        parts.append(text[cursor:end])
    return "".join(parts)


def _find_bracket_offsets(text: str, start: int, end: int) -> list:
    offsets = []
    cursor = start
    while cursor < end:
        if text[cursor] == "[":
            next_lb = text.find("\n", cursor)
            if next_lb == -1 or next_lb >= end:
                break
            line = text[cursor:next_lb]
            if re.match(r"^\[(?:tool:)?[A-Za-z0-9_.:-]+\]$", line):
                offsets.append((cursor, next_lb + 1))
        cursor += 1
    return offsets


def _expand_bracket_offsets(text: str, offsets: list) -> list:
    if not offsets:
        return offsets
    expanded = []
    for start, end in offsets:
        expanded.append((start, end))
    return expanded