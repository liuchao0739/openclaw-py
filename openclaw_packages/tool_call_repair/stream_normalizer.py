from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterable, AsyncGenerator, Callable, Iterable, Optional, Protocol, runtime_checkable

from .grammar import (
    END_TOOL_REQUEST,
    consume_json_tool_closing_marker,
    find_bracketed_json_payload_start,
    find_harmony_json_payload_start,
    find_json_object_end,
    find_xmlish_tool_call_end,
    is_plain_text_tool_name_char,
    is_xmlish_name_char,
    matches_literal_prefix,
    skip_whitespace,
)

TEXT_TOOL_CALL_BUFFER_MAX_CHARS = 256000
TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS = TEXT_TOOL_CALL_BUFFER_MAX_CHARS + 64000
TEXT_TOOL_CALL_SUPPRESSED_TAIL_CHARS = TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS - TEXT_TOOL_CALL_BUFFER_MAX_CHARS
TEXT_TOOL_CALL_SUPPRESSED_MARKER_SCAN_CHARS = 2048

PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE = "possible"
PLAIN_TEXT_TOOL_CALL_BUFFER_IMPOSSIBLE = "impossible"
PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP = "over-cap"

PlainTextToolCallBufferState = str


@runtime_checkable
class PlainTextToolCallNameMatcher(Protocol):
    def has_exact_name(self, name: str) -> bool: ...
    def has_name_prefix(self, prefix: str) -> bool: ...


@dataclass
class PlainTextToolCallMessageNormalization:
    kind: str = ""
    message: dict = field(default_factory=dict)


@dataclass
class PlainTextToolCallStreamNormalizerOptions:
    create_promoted_tool_call_events: Optional[Callable[[dict], Iterable]] = None
    matcher: Optional[PlainTextToolCallNameMatcher] = None
    normalize_done_message: Optional[Callable[[dict], Optional[PlainTextToolCallMessageNormalization]]] = None
    stop_after_done: bool = False


def _as_record(value: Any) -> Optional[dict]:
    return value if isinstance(value, dict) else None


def _could_still_be_json_payload(text: str, start: int) -> bool:
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor >= len(text) or text[cursor] == "{"


def _could_still_be_closing_marker(text: str, start: int) -> bool:
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text):
        return True
    rest = text[cursor:]
    if rest.startswith(END_TOOL_REQUEST):
        return True
    if rest.startswith("[/") and "]" in rest:
        return True
    if rest.startswith("<|call|>"):
        return True
    if rest.startswith("</function>"):
        return True
    return False


def _could_still_be_xmlish_parameter(text: str, start: int) -> bool:
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text):
        return True
    if text[cursor] == "{":
        return True
    return matches_literal_prefix(text[cursor:].lower(), "<parameter=")


def _could_still_be_bracketed_standalone(text: str, matcher: PlainTextToolCallNameMatcher) -> bool:
    if not text.startswith("["):
        return False
    tool_prefix = "[tool:"
    if matches_literal_prefix(text, tool_prefix):
        if len(text) <= len(tool_prefix):
            return True
        cursor = len(tool_prefix)
        while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
            cursor += 1
        name = text[len(tool_prefix):cursor]
        if not name or not matcher.has_name_prefix(name):
            return False
        if cursor >= len(text):
            return True
        if text[cursor] != "]":
            return False
        if not matcher.has_exact_name(name):
            return False
        return (_could_still_be_json_payload(text, cursor + 1)
                or _could_still_be_xmlish_parameter(text, cursor + 1)
                or _could_still_be_closing_marker(text, cursor + 1))
    cursor = 1
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    name = text[1:cursor]
    if not name or not matcher.has_name_prefix(name):
        return False
    if cursor >= len(text):
        return True
    if text[cursor] != "]":
        return False
    if not matcher.has_exact_name(name):
        return False
    cursor += 1
    while cursor < len(text) and text[cursor] in (" ", "\t"):
        cursor += 1
    if cursor >= len(text):
        return True
    if text[cursor] == "\r":
        if cursor + 1 >= len(text):
            return True
        ps = cursor + 2 if text[cursor + 1] == "\n" else cursor + 1
        return (_could_still_be_json_payload(text, ps)
                or _could_still_be_xmlish_parameter(text, ps)
                or _could_still_be_closing_marker(text, ps))
    if text[cursor] != "\n":
        return False
    return (_could_still_be_json_payload(text, cursor + 1)
            or _could_still_be_xmlish_parameter(text, cursor + 1)
            or _could_still_be_closing_marker(text, cursor + 1))


def _could_still_be_xmlish_function(text: str, matcher: PlainTextToolCallNameMatcher) -> bool:
    marker = "<function="
    lower = text.lower()
    if not matches_literal_prefix(lower, marker):
        return False
    if len(text) <= len(marker):
        return True
    cursor = len(marker)
    while cursor < len(text) and is_xmlish_name_char(text[cursor]):
        cursor += 1
    name = text[len(marker):cursor]
    if not name or not matcher.has_name_prefix(name):
        return False
    if cursor >= len(text):
        return True
    if text[cursor] != ">":
        return False
    if not matcher.has_exact_name(name):
        return False
    return _could_still_be_xmlish_parameter(text, cursor + 1) or _could_still_be_closing_marker(text, cursor + 1)


def _could_still_be_harmony_standalone(text: str, matcher: PlainTextToolCallNameMatcher) -> bool:
    ch_marker = "<|channel|>"
    cursor = 0
    if matches_literal_prefix(text, ch_marker):
        if len(text) <= len(ch_marker):
            return True
        cursor = len(ch_marker)
    rest = text[cursor:]
    channel = next((c for c in ["commentary", "analysis", "final"] if matches_literal_prefix(rest, c)), None)
    if not channel:
        return False
    if len(rest) <= len(channel):
        return True
    cursor += len(channel)
    while cursor < len(text) and text[cursor] in (" ", "\t"):
        cursor += 1
    if cursor >= len(text):
        return True
    to_marker = "to="
    to_rest = text[cursor:]
    if not matches_literal_prefix(to_rest, to_marker):
        return False
    if len(to_rest) <= len(to_marker):
        return True
    cursor += len(to_marker)
    name_start = cursor
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    name = text[name_start:cursor]
    if not name or not matcher.has_name_prefix(name):
        return False
    if cursor >= len(text):
        return True
    while cursor < len(text) and text[cursor] in (" ", "\t"):
        cursor += 1
    if cursor >= len(text):
        return True
    if not matcher.has_exact_name(name):
        return False
    code_marker = "code"
    code_rest = text[cursor:]
    if not matches_literal_prefix(code_rest, code_marker):
        return False
    if len(code_rest) <= len(code_marker):
        return True
    cursor += len(code_marker)
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text):
        return True
    msg_marker = "<|message|>"
    msg_rest = text[cursor:]
    if matches_literal_prefix(msg_rest, msg_marker):
        return True
    if text[cursor] == "{":
        return True
    return _could_still_be_closing_marker(text, cursor)


def _has_exact_prefix(text: str, matcher: PlainTextToolCallNameMatcher) -> bool:
    b = re.match(r"^\[(?:tool:)?([A-Za-z0-9_.:-]+)\]", text)
    if b and b.group(1):
        return matcher.has_exact_name(b.group(1))
    x = re.match(r"^<function=([A-Za-z0-9_.:-]+)>", text, re.IGNORECASE)
    if x and x.group(1):
        return matcher.has_exact_name(x.group(1))
    h = re.match(r"^(?:<\|channel\|>)?(?:commentary|analysis|final)\s+to=([A-Za-z0-9_.:-]+)\s+code\b", text)
    return bool(h and h.group(1) and matcher.has_exact_name(h.group(1)))


def _strip_complete_prefix(text: str, matcher: Optional[PlainTextToolCallNameMatcher] = None) -> Optional[str]:
    if matcher and not _has_exact_prefix(text, matcher):
        return None
    xe = find_xmlish_tool_call_end(text)
    if xe is not None:
        return text[xe:]
    js = find_bracketed_json_payload_start(text) or find_harmony_json_payload_start(text)
    if js is None:
        return None
    je = find_json_object_end(text, js)
    if je is None:
        return None
    return text[consume_json_tool_closing_marker(text, je):]


def _strip_prefixes(text: str, matcher: PlainTextToolCallNameMatcher) -> Optional[str]:
    current = text
    changed = False
    for _ in range(32):
        nxt = _strip_complete_prefix(current.lstrip(), matcher)
        if nxt is None:
            if changed and _has_exact_prefix(current.lstrip(), matcher):
                return ""
            return current if changed else None
        changed = True
        current = nxt
        if not current.strip():
            return current
    return "" if _has_exact_prefix(current.lstrip(), matcher) else current


def _get_buffer_state(text: str, matcher: PlainTextToolCallNameMatcher) -> PlainTextToolCallBufferState:
    trimmed = text.lstrip()
    if len(trimmed) == 0:
        return PLAIN_TEXT_TOOL_CALL_BUFFER_IMPOSSIBLE if len(text) > TEXT_TOOL_CALL_BUFFER_MAX_CHARS else PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
    if _is_closing_marker_text(trimmed):
        return PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
    tcl = _could_still_be_bracketed_standalone(trimmed, matcher) or _could_still_be_xmlish_function(trimmed, matcher) or _could_still_be_harmony_standalone(trimmed, matcher)
    if not tcl:
        return PLAIN_TEXT_TOOL_CALL_BUFFER_IMPOSSIBLE
    if len(text) <= TEXT_TOOL_CALL_BUFFER_MAX_CHARS:
        return PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
    stripped = _strip_prefixes(trimmed, matcher)
    if stripped is not None and stripped.strip():
        return PLAIN_TEXT_TOOL_CALL_BUFFER_IMPOSSIBLE
    return PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP


def _get_event_text(event: dict) -> Optional[str]:
    if isinstance(event.get("delta"), str):
        return event["delta"]
    return event.get("content") if isinstance(event.get("content"), str) else None


def _append_buffer(buffered: str, event: dict) -> str:
    text = _get_event_text(event)
    if text is None:
        return buffered
    if isinstance(event.get("content"), str) and not buffered:
        return text
    return (buffered + text) if isinstance(event.get("delta"), str) else buffered


def _has_suppressed_closing_marker(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return (
        END_TOOL_REQUEST.lower() in lower
        or "[/" in lower
        or "<|call|>" in lower
        or "</function>" in lower
    )


def _should_rescan(buffered: str, state: PlainTextToolCallBufferState) -> bool:
    if state != PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP:
        return False
    if len(buffered) <= TEXT_TOOL_CALL_BUFFER_MAX_CHARS:
        return False
    tail = buffered[-TEXT_TOOL_CALL_SUPPRESSED_MARKER_SCAN_CHARS:] if len(buffered) > TEXT_TOOL_CALL_SUPPRESSED_MARKER_SCAN_CHARS else buffered
    return _has_suppressed_closing_marker(tail)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _append_suppressed_buffer(suppressed: str, buffered: str, state: PlainTextToolCallBufferState) -> str:
    if state != PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP:
        return ""
    over_cap_text = buffered
    if len(over_cap_text) > TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS:
        over_cap_text = over_cap_text[:TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS]
    if suppressed:
        combined = suppressed + over_cap_text
        if len(combined) > TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS:
            combined = combined[-TEXT_TOOL_CALL_SUPPRESSED_SCAN_MAX_CHARS:]
        return combined
    return over_cap_text


def _is_closing_marker_text(text: str) -> bool:
    if not text or not text.strip():
        return False
    trimmed = text.strip()
    if trimmed == END_TOOL_REQUEST:
        return True
    if re.match(r"^\[/[A-Za-z0-9_.:-]+\]$", trimmed):
        return True
    if trimmed == "<|call|>":
        return True
    if trimmed == "</function>":
        return True
    return False


def _has_closing_marker_in_text(text: str) -> bool:
    if not text:
        return False
    if END_TOOL_REQUEST in text:
        return True
    if re.search(r"\[/[A-Za-z0-9_.:-]+\]", text):
        return True
    if "<|call|>" in text:
        return True
    if "</function>" in text:
        return True
    return False


def _strip_closing_marker(text: str) -> str:
    if not text:
        return text
    trimmed = text.lstrip()
    if trimmed.startswith(END_TOOL_REQUEST):
        return trimmed[len(END_TOOL_REQUEST):]
    if trimmed.startswith("[/") and "]" in trimmed:
        idx = trimmed.index("]")
        return trimmed[idx + 1:]
    if trimmed.startswith("<|call|>"):
        return trimmed[len("<|call|>"):]
    if trimmed.startswith("</function>"):
        return trimmed[len("</function>"):]
    return text


def _find_tool_call_header_end(text: str, matcher: PlainTextToolCallNameMatcher) -> Optional[int]:
    if not text:
        return None
    if text.startswith("["):
        close = text.find("]")
        if close != -1:
            prefix = text[:close + 1]
            if _has_exact_prefix(prefix, matcher):
                return close + 1
    xml_match = re.match(r"^<function=([A-Za-z0-9_.:-]+)>", text, re.IGNORECASE)
    if xml_match and matcher.has_exact_name(xml_match.group(1)):
        return xml_match.end()
    harmony_match = re.match(r"^(?:<\|channel\|>)?(?:commentary|analysis|final)\s+to=([A-Za-z0-9_.:-]+)\s+code\b", text)
    if harmony_match and matcher.has_exact_name(harmony_match.group(1)):
        return harmony_match.end()
    return None


def _should_suppress_block(text: str, matcher: PlainTextToolCallNameMatcher) -> bool:
    if not text or not text.strip():
        return False
    trimmed = text.lstrip()
    if _is_closing_marker_text(trimmed):
        return True
    if _has_exact_prefix(trimmed, matcher):
        stripped = _strip_prefixes(trimmed, matcher)
        if stripped is not None and not stripped.strip():
            return True
        if stripped is not None and stripped.strip():
            return False
    return _could_still_be_bracketed_standalone(trimmed, matcher) or _could_still_be_xmlish_function(trimmed, matcher) or _could_still_be_harmony_standalone(trimmed, matcher)


def _extract_tool_call_events_from_buffer(
    text: str,
    matcher: PlainTextToolCallNameMatcher,
    options: PlainTextToolCallStreamNormalizerOptions,
) -> Optional[tuple]:
    if not text or not text.strip():
        return None

    promoted_events = []
    remaining = text

    while remaining and remaining.strip():
        stripped = _strip_prefixes(remaining.lstrip(), matcher)
        if stripped is None:
            break

        matched = remaining.lstrip()
        consumed = len(remaining) - len(matched)

        xe = find_xmlish_tool_call_end(matched)
        if xe is not None:
            tool_call_text = matched[:xe]
            if not _has_closing_marker_in_text(tool_call_text):
                remaining = stripped
                continue
            raw_payload = _extract_xmlish_payload(tool_call_text)
            if raw_payload is not None:
                promoted = _promote_tool_call(raw_payload, options)
                if promoted:
                    promoted_events.extend(promoted)
            remaining = remaining[:consumed] + matched[xe:]
            continue

        js_start = find_bracketed_json_payload_start(matched)
        if js_start is None:
            js_start = find_harmony_json_payload_start(matched)
        if js_start is None:
            remaining = stripped
            continue

        je = find_json_object_end(matched, js_start)
        if je is None:
            remaining = stripped
            continue

        raw_json = matched[js_start:je]
        try:
            parsed = json.loads(raw_json)
        except (json.JSONDecodeError, ValueError):
            remaining = stripped
            continue

        closing_end = consume_json_tool_closing_marker(matched, je)
        closing_text = matched[je:closing_end]
        has_closing_marker = (
            END_TOOL_REQUEST in closing_text
            or re.search(r"\[/[A-Za-z0-9_.:-]+\]", closing_text) is not None
            or "<|call|>" in closing_text
        )
        if not has_closing_marker:
            break

        promoted = _promote_tool_call(parsed, options)
        if promoted:
            promoted_events.extend(promoted)

        remaining = remaining[:consumed] + matched[closing_end:]

    if not promoted_events:
        return None
    return promoted_events, remaining


def _extract_xmlish_payload(text: str) -> Optional[dict]:
    params = {}
    pattern = re.compile(
        r"<parameter=([A-Za-z0-9_.:-]+)>(.*?)</parameter",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        value = m.group(2).strip()
        try:
            params[name] = json.loads(value)
        except (ValueError, json.JSONDecodeError):
            params[name] = value
    if params:
        return params

    json_start = text.find("{")
    if json_start != -1:
        json_end = text.rfind("}")
        if json_end != -1 and json_end > json_start:
            json_str = text[json_start:json_end + 1]
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def _promote_tool_call(parsed: dict, options: PlainTextToolCallStreamNormalizerOptions) -> list:
    if options.create_promoted_tool_call_events is None:
        return []
    events = options.create_promoted_tool_call_events(parsed)
    return list(events) if events else []


def _scrub_buffered_from_content(buffered: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not buffered or not buffered.strip():
        return ""
    stripped = _strip_prefixes(buffered.lstrip(), matcher)
    if stripped is None:
        header_end = _find_tool_call_header_end(buffered.lstrip(), matcher)
        if header_end is not None and header_end > 0:
            leading = buffered[:len(buffered) - len(buffered.lstrip())]
            return leading + buffered.lstrip()[header_end:]
        return buffered
    leading = buffered[:len(buffered) - len(buffered.lstrip())]
    return leading + stripped


def _scrub_over_cap_prefix_from_content(content: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not content or not content.strip():
        return content
    trimmed = content.lstrip()
    if not _has_exact_prefix(trimmed, matcher):
        return content
    stripped = _strip_prefixes(trimmed, matcher)
    if stripped is None:
        header_end = _find_tool_call_header_end(trimmed, matcher)
        if header_end is not None and header_end > 0:
            leading = content[:len(content) - len(trimmed)]
            return leading + trimmed[header_end:]
        return content
    leading = content[:len(content) - len(trimmed)]
    return leading + stripped


def _scrub_first_over_cap_prefix(content: str, matcher: PlainTextToolCallNameMatcher) -> str:
    return _scrub_over_cap_prefix_from_content(content, matcher)


def _scrub_suppressed_indexes(text: str, matcher: PlainTextToolCallNameMatcher) -> list:
    indexes = []
    if not text:
        return indexes
    cursor = 0
    while cursor < len(text):
        if _has_exact_prefix(text[cursor:], matcher):
            stripped = _strip_prefixes(text[cursor:], matcher)
            if stripped is not None and stripped != text[cursor:]:
                end = len(text) - len(stripped)
                indexes.append((cursor, end))
                cursor = end
                continue
            header_end = _find_tool_call_header_end(text[cursor:], matcher)
            if header_end is not None and header_end > 0:
                indexes.append((cursor, cursor + header_end))
                cursor += header_end
                continue
        cursor += 1
    return indexes


def _strip_tool_calls_from_content(content: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not content or not content.strip():
        return content
    result = []
    cursor = 0
    while cursor < len(content):
        if _has_exact_prefix(content[cursor:], matcher):
            stripped = _strip_prefixes(content[cursor:], matcher)
            if stripped is not None and stripped != content[cursor:]:
                cursor = len(content) - len(stripped)
                continue
            header_end = _find_tool_call_header_end(content[cursor:], matcher)
            if header_end is not None and header_end > 0:
                cursor += header_end
                continue
        result.append(content[cursor])
        cursor += 1
    return "".join(result)


def _strip_over_cap_from_content(content: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not content:
        return content
    return _scrub_over_cap_prefix_from_content(content, matcher)


def _scrub_content(content: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not content or not isinstance(content, str):
        return content
    return _strip_tool_calls_from_content(content, matcher)


def _should_preserve_empty_blocks(text: str) -> bool:
    if not text or not text.strip():
        return True
    return not text.lstrip()


def _scrub_buffered_from_partial(partial_text: str, matcher: PlainTextToolCallNameMatcher) -> str:
    if not partial_text:
        return ""
    if _has_exact_prefix(partial_text, matcher):
        stripped = _strip_prefixes(partial_text, matcher)
        if stripped is not None:
            return stripped
        header_end = _find_tool_call_header_end(partial_text, matcher)
        if header_end is not None and header_end > 0:
            return partial_text[header_end:]
    return partial_text


def _scrub_buffered_from_message(message: dict, matcher: PlainTextToolCallNameMatcher) -> dict:
    content = message.get("content", "")
    if not isinstance(content, str) or not content:
        return message
    scrubbed = _scrub_content(content, matcher)
    if scrubbed == content:
        return message
    result = dict(message)
    result["content"] = scrubbed
    if "delta" in result:
        result["delta"] = scrubbed
    return result


def _scrub_buffered_from_error(error: dict, matcher: PlainTextToolCallNameMatcher) -> dict:
    return error


def _replace_text_with_visible_suffix(text: str, suffix: str) -> str:
    return suffix


def scrub_over_cap_plain_text_tool_call_message(
    message: dict,
    matcher: PlainTextToolCallNameMatcher,
) -> dict:
    content = message.get("content", "")
    if not isinstance(content, str) or not content:
        return message
    scrubbed = _scrub_over_cap_prefix_from_content(content, matcher)
    if scrubbed == content:
        return message
    result = dict(message)
    result["content"] = scrubbed
    return result


async def normalize_plain_text_tool_call_stream_events(
    events: AsyncIterable[dict],
    options: Optional[PlainTextToolCallStreamNormalizerOptions] = None,
) -> AsyncGenerator[dict, None]:
    matcher = options.matcher if options else None
    if matcher is None:
        async for event in events:
            yield event
        return

    buffer = ""
    suppressed = ""
    state: PlainTextToolCallBufferState = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE

    async for event in events:
        text = _get_event_text(event)

        if text is None:
            if options and options.normalize_done_message:
                norm = options.normalize_done_message(event)
                if norm is not None:
                    if buffer:
                        scrubbed = _scrub_buffered_from_content(buffer, matcher)
                        if scrubbed:
                            yield {"content": scrubbed}
                    yield norm.message
                    buffer = ""
                    suppressed = ""
                    state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
                    if options.stop_after_done:
                        break
                    continue

            if buffer:
                should_suppress = _should_suppress_block(buffer, matcher)
                if should_suppress:
                    if _is_closing_marker_text(buffer.lstrip()):
                        buffer = ""
                        suppressed = ""
                        state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
                    else:
                        visible = _replace_text_with_visible_suffix(buffer, "[tool call suppressed]")
                        yield {"content": visible}
                        buffer = ""
                        suppressed = ""
                        state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
                else:
                    scrubbed = _scrub_content(buffer, matcher)
                    if scrubbed:
                        yield {"content": scrubbed}
                    buffer = ""
                    suppressed = ""
                    state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE

            yield event
            continue

        buffer = _append_buffer(buffer, event)
        new_state = _get_buffer_state(buffer, matcher)

        if new_state == PLAIN_TEXT_TOOL_CALL_BUFFER_IMPOSSIBLE:
            if buffer:
                while buffer and _is_closing_marker_text(buffer.lstrip()):
                    buffer = _strip_closing_marker(buffer)
                if buffer:
                    scrubbed = _scrub_content(buffer, matcher)
                    if scrubbed:
                        yield {"content": scrubbed}
            buffer = ""
            suppressed = ""
            state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
            continue

        if new_state == PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP:
            state = PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP
            suppressed = _append_suppressed_buffer(suppressed, buffer, state)

            while suppressed and suppressed.strip():
                extracted = _extract_tool_call_events_from_buffer(suppressed, matcher, options)
                if extracted is None:
                    break
                tool_call_events, remaining = extracted
                for tce in tool_call_events:
                    yield tce
                suppressed = remaining
                if not _should_rescan(suppressed, state):
                    break
            continue

        state = new_state

        while buffer and buffer.strip():
            extracted = _extract_tool_call_events_from_buffer(buffer, matcher, options)
            if extracted is None:
                break
            tool_call_events, remaining = extracted
            for tce in tool_call_events:
                yield tce
            buffer = remaining

        if buffer and buffer.strip():
            should_suppress = _should_suppress_block(buffer, matcher)
            if should_suppress:
                if _is_closing_marker_text(buffer.lstrip()):
                    buffer = ""
                    state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE
            else:
                scrubbed = _scrub_content(buffer, matcher)
                if scrubbed:
                    yield {"content": scrubbed}
                buffer = ""
                state = PLAIN_TEXT_TOOL_CALL_BUFFER_POSSIBLE

    if buffer:
        if state == PLAIN_TEXT_TOOL_CALL_BUFFER_OVER_CAP and suppressed:
            while suppressed and suppressed.strip():
                extracted = _extract_tool_call_events_from_buffer(suppressed, matcher, options)
                if extracted is None:
                    break
                tool_call_events, remaining = extracted
                for tce in tool_call_events:
                    yield tce
                suppressed = remaining
        else:
            while buffer and _is_closing_marker_text(buffer.lstrip()):
                buffer = _strip_closing_marker(buffer)
            if buffer and buffer.strip():
                if _should_suppress_block(buffer, matcher):
                    visible = _replace_text_with_visible_suffix(buffer, "[tool call suppressed]")
                    yield {"content": visible}
                else:
                    scrubbed = _scrub_content(buffer, matcher)
                    if scrubbed:
                        yield {"content": scrubbed}

    if suppressed:
        scrubbed = _scrub_content(suppressed, matcher)
        if scrubbed:
            yield {"content": scrubbed}
