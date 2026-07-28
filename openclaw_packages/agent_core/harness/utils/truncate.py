from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_BYTES = 50 * 1024
GREP_MAX_LINE_LENGTH = 500

TruncatedBy = Literal["lines", "bytes", None]


@dataclass
class TruncationResult:
    content: str
    truncated: bool
    truncatedBy: TruncatedBy
    totalLines: int
    totalBytes: int
    outputLines: int
    outputBytes: int
    lastLinePartial: bool = False
    firstLineExceedsLimit: bool = False
    maxLines: int = DEFAULT_MAX_LINES
    maxBytes: int = DEFAULT_MAX_BYTES


@dataclass
class TruncationOptions:
    maxLines: int | None = None
    maxBytes: int | None = None


def split_lines_for_counting(content: str) -> list[str]:
    if len(content) == 0:
        return []
    lines = content.split("\n")
    if content.endswith("\n"):
        lines.pop()
    return lines


def find_first_non_ascii(content: str) -> int:
    for index, ch in enumerate(content):
        if ord(ch) > 0x7F:
            return index
    return -1


def utf8_byte_length(content: str) -> int:
    try:
        return len(content.encode("utf-8"))
    except UnicodeEncodeError:
        return len(content.encode("utf-8", errors="replace"))


def replace_unpaired_surrogates(content: str) -> str:
    output = []
    i = 0
    while i < len(content):
        code = ord(content[i])
        if 0xD800 <= code <= 0xDBFF:
            if i + 1 < len(content):
                next_code = ord(content[i + 1])
                if 0xDC00 <= next_code <= 0xDFFF:
                    output.append(content[i] + content[i + 1])
                    i += 2
                    continue
            output.append("\ufffd")
        elif 0xDC00 <= code <= 0xDFFF:
            output.append("\ufffd")
        else:
            output.append(content[i])
        i += 1
    return "".join(output)


def format_size(bytes: int) -> str:
    if bytes < 1024:
        return f"{bytes}B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f}KB"
    return f"{bytes / (1024 * 1024):.1f}MB"


def _resolve_truncation_input(
    content: str,
    options: TruncationOptions,
) -> dict:
    max_lines = options.maxLines if options.maxLines is not None else DEFAULT_MAX_LINES
    max_bytes = options.maxBytes if options.maxBytes is not None else DEFAULT_MAX_BYTES
    total_bytes = utf8_byte_length(content)
    lines = split_lines_for_counting(content)
    return {
        "lines": lines,
        "totalLines": len(lines),
        "totalBytes": total_bytes,
        "maxLines": max_lines,
        "maxBytes": max_bytes,
    }


def _build_truncation_result(
    input_data: dict,
    content: str,
    truncated: bool,
    truncated_by: TruncatedBy,
    output_lines: int,
    output_bytes: int | None = None,
    last_line_partial: bool = False,
    first_line_exceeds_limit: bool = False,
) -> TruncationResult:
    return TruncationResult(
        content=content,
        truncated=truncated,
        truncatedBy=truncated_by,
        totalLines=input_data["totalLines"],
        totalBytes=input_data["totalBytes"],
        outputLines=output_lines,
        outputBytes=output_bytes if output_bytes is not None else utf8_byte_length(content),
        lastLinePartial=last_line_partial,
        firstLineExceedsLimit=first_line_exceeds_limit,
        maxLines=input_data["maxLines"],
        maxBytes=input_data["maxBytes"],
    )


def truncate_head(content: str, options: TruncationOptions | None = None) -> TruncationResult:
    if options is None:
        options = TruncationOptions()
    input_data = _resolve_truncation_input(content, options)

    if input_data["totalLines"] <= input_data["maxLines"] and input_data["totalBytes"] <= input_data["maxBytes"]:
        return _build_truncation_result(
            input_data,
            content,
            False,
            None,
            input_data["totalLines"],
            input_data["totalBytes"],
        )

    first_line_bytes = utf8_byte_length(input_data["lines"][0])
    if first_line_bytes > input_data["maxBytes"]:
        return _build_truncation_result(
            input_data,
            "",
            True,
            "bytes",
            0,
            0,
            first_line_exceeds_limit=True,
        )

    output_lines_arr: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = (
        "lines" if input_data["totalLines"] > input_data["maxLines"] else "bytes"
    )

    for i in range(min(len(input_data["lines"]), input_data["maxLines"])):
        line = input_data["lines"][i]
        line_bytes = utf8_byte_length(line) + (1 if i > 0 else 0)

        if output_bytes_count + line_bytes > input_data["maxBytes"]:
            truncated_by = "bytes"
            break

        output_lines_arr.append(line)
        output_bytes_count += line_bytes

    if (
        input_data["totalLines"] > input_data["maxLines"]
        and len(output_lines_arr) >= input_data["maxLines"]
        and output_bytes_count <= input_data["maxBytes"]
    ):
        truncated_by = "lines"

    output_content = "\n".join(output_lines_arr)

    return _build_truncation_result(
        input_data,
        output_content,
        True,
        truncated_by,
        len(output_lines_arr),
    )


def _truncate_string_to_bytes_from_end(s: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""

    output_bytes = 0
    start = len(s)
    needs_replacement = False
    i = len(s)
    while i > 0:
        character_start = i - 1
        code = ord(s[character_start])
        character_bytes: int
        unpaired_surrogate = False
        if 0xDC00 <= code <= 0xDFFF and character_start > 0:
            previous = ord(s[character_start - 1])
            if 0xD800 <= previous <= 0xDBFF:
                character_start -= 1
                character_bytes = 4
            else:
                character_bytes = 3
                unpaired_surrogate = True
        elif 0xD800 <= code <= 0xDBFF:
            character_bytes = 3
            unpaired_surrogate = True
        else:
            character_bytes = 1 if code <= 0x7F else 2 if code <= 0x7FF else 3
        if output_bytes + character_bytes > max_bytes:
            break
        output_bytes += character_bytes
        start = character_start
        needs_replacement = needs_replacement or unpaired_surrogate
        i = character_start

    output = s[start:]
    return replace_unpaired_surrogates(output) if needs_replacement else output


def truncate_tail(content: str, options: TruncationOptions | None = None) -> TruncationResult:
    if options is None:
        options = TruncationOptions()
    input_data = _resolve_truncation_input(content, options)

    if input_data["totalLines"] <= input_data["maxLines"] and input_data["totalBytes"] <= input_data["maxBytes"]:
        return _build_truncation_result(
            input_data,
            content,
            False,
            None,
            input_data["totalLines"],
            input_data["totalBytes"],
        )

    output_lines_arr: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = (
        "lines" if input_data["totalLines"] > input_data["maxLines"] else "bytes"
    )
    last_line_partial = False

    i = len(input_data["lines"]) - 1
    while i >= 0 and len(output_lines_arr) < input_data["maxLines"]:
        line = input_data["lines"][i]
        line_bytes = utf8_byte_length(line) + (1 if len(output_lines_arr) > 0 else 0)

        if output_bytes_count + line_bytes > input_data["maxBytes"]:
            truncated_by = "bytes"
            if len(output_lines_arr) == 0:
                truncated_line = _truncate_string_to_bytes_from_end(line, input_data["maxBytes"])
                output_lines_arr.insert(0, truncated_line)
                output_bytes_count = utf8_byte_length(truncated_line)
                last_line_partial = True
            break

        output_lines_arr.insert(0, line)
        output_bytes_count += line_bytes
        i -= 1

    if (
        input_data["totalLines"] > input_data["maxLines"]
        and len(output_lines_arr) >= input_data["maxLines"]
        and output_bytes_count <= input_data["maxBytes"]
    ):
        truncated_by = "lines"

    output_content = "\n".join(output_lines_arr)

    return _build_truncation_result(
        input_data,
        output_content,
        True,
        truncated_by,
        len(output_lines_arr),
        last_line_partial=last_line_partial,
    )


def truncate_line(
    line: str,
    max_chars: int = GREP_MAX_LINE_LENGTH,
) -> tuple[str, bool]:
    if len(line) <= max_chars:
        return (line, False)
    return (f"{line[:max_chars]}... [truncated]", True)