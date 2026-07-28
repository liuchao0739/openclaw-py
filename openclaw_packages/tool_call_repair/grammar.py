import re
from typing import Optional

END_TOOL_REQUEST = "[END_TOOL_REQUEST]"
HARMONY_CHANNEL_MARKER = "<|channel|>"
HARMONY_MESSAGE_MARKER = "<|message|>"
HARMONY_CALL_MARKER = "<|call|>"


def matches_literal_prefix(text: str, literal: str) -> bool:
    return literal.startswith(text) or text.startswith(literal)


def is_plain_text_tool_name_char(char: Optional[str]) -> bool:
    return bool(char and re.match(r"[A-Za-z0-9_.:-]", char))


def is_xmlish_name_char(char: Optional[str]) -> bool:
    return bool(char and re.match(r"[A-Za-z0-9_.:-]", char))


def skip_horizontal_whitespace(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index] in (" ", "\t"):
        index += 1
    return index


def skip_whitespace(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def consume_line_break(text: str, start: int) -> Optional[int]:
    if start >= len(text):
        return None
    if text[start] == "\r":
        if start + 1 < len(text) and text[start + 1] == "\n":
            return start + 2
        return start + 1
    if text[start] == "\n":
        return start + 1
    return None


def find_json_object_end(text: str, start: int, max_payload_bytes: Optional[int] = None) -> Optional[int]:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        if max_payload_bytes is not None and (index + 1 - start) > max_payload_bytes:
            return None
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def skip_serialized_tool_call_trailing_line_break(text: str, cursor: int) -> int:
    after_line_break = consume_line_break(text, cursor)
    return after_line_break if after_line_break is not None else cursor


def consume_json_tool_closing_marker(text: str, cursor: int) -> int:
    marker_start = cursor
    while marker_start < len(text) and text[marker_start].isspace():
        marker_start += 1
    rest = text[marker_start:]
    if rest.startswith(END_TOOL_REQUEST):
        return skip_serialized_tool_call_trailing_line_break(text, marker_start + len(END_TOOL_REQUEST))
    bracket_close = re.match(r"^\[\/[A-Za-z0-9_.:-]+\]", rest)
    if bracket_close:
        return skip_serialized_tool_call_trailing_line_break(text, marker_start + len(bracket_close.group(0)))
    if rest.startswith(HARMONY_CALL_MARKER):
        return skip_serialized_tool_call_trailing_line_break(text, marker_start + len(HARMONY_CALL_MARKER))
    if rest.startswith('</function>'):
        return skip_serialized_tool_call_trailing_line_break(text, marker_start + len('</function>'))
    return skip_serialized_tool_call_trailing_line_break(text, cursor)


def find_bracketed_json_payload_start(text: str) -> Optional[int]:
    if not text.startswith("["):
        return None
    close = text.find("]")
    if close == -1:
        return None
    cursor = close + 1
    cursor = skip_horizontal_whitespace(text, cursor)
    cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
    cursor = skip_horizontal_whitespace(text, cursor)
    return cursor if cursor < len(text) and text[cursor] == "{" else None


def find_harmony_json_payload_start(text: str) -> Optional[int]:
    cursor = 0
    if text.startswith(HARMONY_CHANNEL_MARKER):
        cursor = len(HARMONY_CHANNEL_MARKER)
    rest = text[cursor:]
    channel = None
    for candidate in ["commentary", "analysis", "final"]:
        if rest.startswith(candidate):
            channel = candidate
            break
    if not channel:
        return None
    cursor += len(channel)
    cursor = skip_horizontal_whitespace(text, cursor)
    if not text[cursor:].startswith("to="):
        return None
    cursor += 3
    name_start = cursor
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    if cursor == name_start:
        return None
    cursor = skip_horizontal_whitespace(text, cursor)
    if not text[cursor:].startswith("code"):
        return None
    cursor += 4
    cursor = skip_whitespace(text, cursor)
    if text[cursor:].startswith(HARMONY_MESSAGE_MARKER):
        cursor = skip_whitespace(text, cursor + len(HARMONY_MESSAGE_MARKER))
    return cursor if cursor < len(text) and text[cursor] == "{" else None


def starts_with_ascii_marker_ignore_case(text: str, cursor: int, marker: str) -> bool:
    return text[cursor:cursor + len(marker)].lower() == marker


def index_of_ascii_marker_ignore_case(text: str, marker: str, start: int) -> int:
    cursor = start
    while cursor < len(text):
        next_pos = text.find(marker[0], cursor)
        if next_pos == -1:
            return -1
        if starts_with_ascii_marker_ignore_case(text, next_pos, marker):
            return next_pos
        cursor = next_pos + 1
    return -1


def find_xmlish_tool_call_end(text: str) -> Optional[int]:
    xml_function = re.match(r"^<function=[A-Za-z0-9_.:-]+>", text, re.IGNORECASE)
    if xml_function:
        cursor = len(xml_function.group(0))
        cursor = skip_horizontal_whitespace(text, cursor)
        cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
    else:
        bracketed = re.match(r"^\[(?:tool:)?[A-Za-z0-9_.:-]+\]", text)
        if not bracketed:
            return None
        cursor = len(bracketed.group(0))
        cursor = skip_horizontal_whitespace(text, cursor)
        cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)

    cursor = skip_whitespace(text, cursor)

    if starts_with_ascii_marker_ignore_case(text, cursor, "<parameter="):
        while cursor < len(text):
            parameter_close = index_of_ascii_marker_ignore_case(text, "</parameter", cursor)
            if parameter_close == -1:
                return None
            cursor = parameter_close + len("</parameter")
            cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
            cursor = skip_whitespace(text, cursor)
            if starts_with_ascii_marker_ignore_case(text, cursor, "<parameter="):
                continue
            break

        function_close = index_of_ascii_marker_ignore_case(text, "</function", cursor)
        if function_close != -1:
            cursor = function_close + len("</function")
            return skip_serialized_tool_call_trailing_line_break(text, cursor)
        return None

    if cursor < len(text) and text[cursor] == "{":
        json_end = find_json_object_end(text, cursor)
        if json_end is None:
            return None
        cursor = json_end
        cursor = skip_whitespace(text, cursor)
        cursor = consume_json_tool_closing_marker(text, cursor)
        return cursor

    return None



def extract_standalone_plain_text_tool_call_text(text: str, start: int) -> Optional[tuple[str, int]]:
    cursor = start
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    if cursor == start:
        return None
    tool_name = text[start:cursor]
    cursor = skip_horizontal_whitespace(text, cursor)
    if cursor >= len(text) or text[cursor] != "(":
        return None
    depth = 0
    arg_start = cursor
    while cursor < len(text):
        char = text[cursor]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                cursor += 1
                break
        cursor += 1
    if depth != 0:
        return None
    arg_text = text[arg_start:cursor]
    cursor = skip_horizontal_whitespace(text, cursor)
    cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
    return tool_name + arg_text, cursor


def parse_standalone_plain_text_tool_call_blocks(text: str) -> list[dict]:
    blocks = []
    cursor = 0
    while cursor < len(text):
        if is_plain_text_tool_name_char(text[cursor]):
            result = extract_standalone_plain_text_tool_call_text(text, cursor)
            if result is not None:
                call_text, end = result
                blocks.append({"text": call_text, "start": cursor, "end": end})
                cursor = end
                continue
        cursor += 1
    return blocks


def strip_plain_text_tool_call_blocks(text: str) -> str:
    blocks = parse_standalone_plain_text_tool_call_blocks(text)
    if not blocks:
        return text
    parts = []
    prev_end = 0
    for block in blocks:
        parts.append(text[prev_end:block["start"]])
        prev_end = block["end"]
    parts.append(text[prev_end:])
    return "".join(parts)


def find_xmlish_tool_call_end(text: str) -> Optional[int]:
    xml_function = re.match(r"^<function=[A-Za-z0-9_.:-]+>", text, re.IGNORECASE)
    if xml_function:
        cursor = len(xml_function.group(0))
        cursor = skip_horizontal_whitespace(text, cursor)
        cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
    else:
        bracketed = re.match(r"^\[(?:tool:)?[A-Za-z0-9_.:-]+\]", text)
        if not bracketed:
            return None
        cursor = len(bracketed.group(0))
        cursor = skip_horizontal_whitespace(text, cursor)
        cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)

    cursor = skip_whitespace(text, cursor)

    if starts_with_ascii_marker_ignore_case(text, cursor, "<parameter="):
        while cursor < len(text):
            parameter_close = index_of_ascii_marker_ignore_case(text, "</parameter>", cursor)
            if parameter_close == -1:
                return None
            cursor = parameter_close + len("</parameter>")
            cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
            cursor = skip_whitespace(text, cursor)
            if starts_with_ascii_marker_ignore_case(text, cursor, "<parameter="):
                continue
            break

        function_close = index_of_ascii_marker_ignore_case(text, "</function>", cursor)
        if function_close != -1:
            cursor = function_close + len("</function>")
            return skip_serialized_tool_call_trailing_line_break(text, cursor)
        return None

    if cursor < len(text) and text[cursor] == "{":
        json_end = find_json_object_end(text, cursor)
        if json_end is None:
            return None
        cursor = json_end
        cursor = skip_whitespace(text, cursor)
        cursor = consume_json_tool_closing_marker(text, cursor)
        return cursor

    return None



def extract_standalone_plain_text_tool_call_text(text: str, start: int) -> Optional[tuple[str, int]]:
    cursor = start
    while cursor < len(text) and is_plain_text_tool_name_char(text[cursor]):
        cursor += 1
    if cursor == start:
        return None
    tool_name = text[start:cursor]
    cursor = skip_horizontal_whitespace(text, cursor)
    if cursor >= len(text) or text[cursor] != "(":
        return None
    depth = 0
    arg_start = cursor
    while cursor < len(text):
        char = text[cursor]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                cursor += 1
                break
        cursor += 1
    if depth != 0:
        return None
    arg_text = text[arg_start:cursor]
    cursor = skip_horizontal_whitespace(text, cursor)
    cursor = skip_serialized_tool_call_trailing_line_break(text, cursor)
    return tool_name + arg_text, cursor


def parse_standalone_plain_text_tool_call_blocks(text: str) -> list[dict]:
    blocks = []
    cursor = 0
    while cursor < len(text):
        if is_plain_text_tool_name_char(text[cursor]):
            result = extract_standalone_plain_text_tool_call_text(text, cursor)
            if result is not None:
                call_text, end = result
                blocks.append({"text": call_text, "start": cursor, "end": end})
                cursor = end
                continue
        cursor += 1
    return blocks


def strip_plain_text_tool_call_blocks(text: str) -> str:
    blocks = parse_standalone_plain_text_tool_call_blocks(text)
    if not blocks:
        return text
    parts = []
    prev_end = 0
    for block in blocks:
        parts.append(text[prev_end:block["start"]])
        prev_end = block["end"]
    parts.append(text[prev_end:])
    return "".join(parts)
