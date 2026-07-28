from __future__ import annotations

import re
from typing import Literal

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw_packages.tool_call_repair import (
    strip_plain_text_tool_call_blocks,
)

from ._tool_call_xml import (
    strip_legacy_bracket_tool_call_blocks,
    strip_minimax_tool_call_xml,
    strip_tool_call_xml_tags,
)
from .code_regions import find_code_regions, is_inside_code
from .model_special_tokens import strip_model_special_tokens
from .reasoning_tags import (
    ReasoningTagMode,
    ReasoningTagTrim,
    strip_reasoning_tags_from_text,
)

AssistantVisibleTextSanitizerProfile = Literal[
    "delivery",
    "history",
    "internal-scaffolding",
    "tool-progress",
]

_MEMORY_TAG_RE = re.compile(
    r"<\s*(\/?)\s*relevant[-_]memories\b[^<>]*>", re.IGNORECASE
)
_MEMORY_TAG_QUICK_RE = re.compile(
    r"<\s*\/?\s*relevant[-_]memories\b", re.IGNORECASE
)
_INTERNAL_TRACE_LINE_QUICK_RE = re.compile(
    r"(?:📊|🛠️|📖|📝|🔍|🔎|⚙️|tool[-_ ]?call|tool[-_ ]?result|function[-_ ]?call)",
    re.IGNORECASE,
)
_INTERNAL_TRACE_LINE_RE = re.compile(
    r"^(?:>\s*)?(?:⚠️\s*)?(?:📊|🛠️|📖|📝|🔍|🔎|⚙️)\s*(?:Session Status|Exec|Read|Edit|Write|Patch|Search|Open|Click|Find|Screenshot|Update Plan|Tool Call|Tool Result|Function Call|Shell|Command)\s*:",
    re.IGNORECASE,
)
_INTERNAL_COMPACT_FAILURE_TRACE_LINE_RE = re.compile(
    r"^(?:>\s*)?⚠️\s*🛠️\s+\S[\s\S]*\s+\(agent\)`{0,2}\s+failed(?:\s*:.*)?\s*$",
    re.IGNORECASE,
)
_INTERNAL_COMPACT_COMMAND_TRACE_LINE_RE = re.compile(
    r"^(?:>\s*)?🛠️\s*(?:(?:(?:elevated|pty)\b\s*(?:·|,)\s*)+)?(?:`{1,2}\s*\S|(?:run|check|fetch|pull|push|view|show|list|switch|create|merge|rebase|stage|restore|reset|stash|search|find|print|copy|move|remove|install|start|cd|git|pnpm|npm|yarn|bun|node|python|python3|bash|sh)\b)",
    re.IGNORECASE,
)
_INTERNAL_CHANNEL_TRACE_LINE_RE = re.compile(
    r"^(?:>\s*)?(?:tool[-_ ]?call|tool[-_ ]?result|function[-_ ]?call)\s*[:=]",
    re.IGNORECASE,
)
_TOOL_TEXT_PREFILTER_RE = re.compile(
    r"(?:tool[_\s-]?calls?|function[_\s-]?call|[\"'](?:name|tool_name|function|arguments|args|input|parameters|tool_calls)[\"']|<\s*tool_call\b|Action\s*:|\[END_TOOL_REQUEST\])",
    re.IGNORECASE,
)


def _consume_jsonish(
    input_text: str,
    start: int,
    allow_leading_newlines: bool = False,
) -> int | None:
    index = start
    n = len(input_text)
    while index < n:
        ch = input_text[index]
        if ch in (" ", "\t"):
            index += 1
            continue
        if allow_leading_newlines and ch in ("\n", "\r"):
            index += 1
            continue
        break
    if index >= n:
        return None

    start_char = input_text[index]
    if start_char in ("{", "["):
        depth = 0
        in_string = False
        escape = False
        for idx in range(index, n):
            ch = input_text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch in ("{", "["):
                depth += 1
            elif ch in ("}", "]"):
                depth -= 1
                if depth == 0:
                    return idx + 1
        return None

    if start_char == '"':
        escape = False
        for idx in range(index + 1, n):
            ch = input_text[idx]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                return idx + 1
        return None

    end = index
    while end < n and input_text[end] not in ("\n", "\r"):
        end += 1
    return end


_TOOL_CALL_RE = re.compile(r"\[Tool Call:[^\]]*\]", re.IGNORECASE)


def _strip_tool_calls(input_text: str) -> str:
    result: list[str] = []
    cursor = 0
    for match in _TOOL_CALL_RE.finditer(input_text):
        start = match.start()
        if start < cursor:
            continue
        result.append(input_text[cursor:start])
        index = start + len(match.group(0))
        while index < len(input_text) and input_text[index] in (" ", "\t"):
            index += 1
        if index < len(input_text) and input_text[index] == "\r":
            index += 1
            if index < len(input_text) and input_text[index] == "\n":
                index += 1
        elif index < len(input_text) and input_text[index] == "\n":
            index += 1
        while index < len(input_text) and input_text[index] in (" ", "\t"):
            index += 1
        if (
            normalize_lowercase_string_or_empty(input_text[index : index + 9])
            == "arguments"
        ):
            index += 9
            if index < len(input_text) and input_text[index] == ":":
                index += 1
            if index < len(input_text) and input_text[index] == " ":
                index += 1
            end = _consume_jsonish(input_text, index, allow_leading_newlines=True)
            if end is not None:
                index = end
        if index < len(input_text) and input_text[index] in ("\n", "\r"):
            last_result = "".join(result) if result else ""
            if last_result.endswith(("\n", "\r")) or not last_result:
                if input_text[index] == "\r":
                    index += 1
                if index < len(input_text) and input_text[index] == "\n":
                    index += 1
        cursor = index
    result.append(input_text[cursor:])
    return "".join(result)


_TOOL_RESULT_RE = re.compile(
    r"\[Tool Result for ID[^\]]*\]\n?[\s\S]*?(?=\n*\[Tool |\n*$)",
    re.IGNORECASE,
)
_HISTORICAL_CONTEXT_RE = re.compile(r"\[Historical context:[^\]]*\]\n?", re.IGNORECASE)


def strip_downgraded_tool_call_text(text: str) -> str:
    if not text:
        return text
    if not (
        re.search(r"\[Tool (?:Call|Result)", text, re.IGNORECASE)
        or re.search(r"\[Historical context", text, re.IGNORECASE)
    ):
        return text

    cleaned = _strip_tool_calls(text)
    cleaned = _TOOL_RESULT_RE.sub("", cleaned)
    cleaned = _HISTORICAL_CONTEXT_RE.sub("", cleaned)
    return cleaned.strip()


def _strip_relevant_memories_tags(text: str) -> str:
    if not text or not _MEMORY_TAG_QUICK_RE.search(text):
        return text

    code_regions = find_code_regions(text)
    result: list[str] = []
    last_index = 0
    in_memory_block = False

    for match in _MEMORY_TAG_RE.finditer(text):
        idx = match.start()
        if is_inside_code(idx, code_regions):
            continue

        is_close = match.group(1) == "/"
        if not in_memory_block:
            result.append(text[last_index:idx])
            if not is_close:
                in_memory_block = True
        elif is_close:
            in_memory_block = False

        last_index = idx + len(match.group(0))

    if not in_memory_block:
        result.append(text[last_index:])

    return "".join(result)


def strip_assistant_internal_trace_lines(text: str) -> str:
    if not text or not _INTERNAL_TRACE_LINE_QUICK_RE.search(text):
        return text

    code_regions = find_code_regions(text)
    result: list[str] = []
    line_start = 0
    while line_start < len(text):
        newline_index = text.find("\n", line_start)
        line_end = newline_index + 1 if newline_index != -1 else len(text)
        raw_line = text[line_start:line_end]
        line = raw_line[:-1].rstrip("\r") if raw_line.endswith("\n") else raw_line
        trimmed = line.strip()
        should_strip = (
            not is_inside_code(line_start, code_regions)
            and bool(
                _INTERNAL_TRACE_LINE_RE.search(trimmed)
                or _INTERNAL_COMPACT_FAILURE_TRACE_LINE_RE.search(trimmed)
                or _INTERNAL_COMPACT_COMMAND_TRACE_LINE_RE.search(trimmed)
                or _INTERNAL_CHANNEL_TRACE_LINE_RE.search(trimmed)
            )
        )
        if not should_strip:
            result.append(raw_line)
        line_start = line_end
    return "".join(result)


def _strip_reasoning(value: str, mode: ReasoningTagMode, trim: ReasoningTagTrim) -> str:
    return strip_reasoning_tags_from_text(value, mode=mode, trim=trim)


def _apply_final_trim(value: str, final_trim: ReasoningTagTrim) -> str:
    if final_trim == "none":
        return value
    if final_trim == "start":
        return value.lstrip()
    return value.strip()


def _strip_non_reasoning_stages(
    value: str,
    preserve_minimax_tool_xml: bool,
    strip_function_calls_xml_payloads: bool,
    strip_function_response_after_plural_tool_calls: bool,
    strip_internal_trace_lines: bool,
    preserve_downgraded_tool_text: bool,
) -> str:
    cleaned = value
    if not preserve_minimax_tool_xml:
        cleaned = strip_minimax_tool_call_xml(cleaned)
    cleaned = strip_model_special_tokens(cleaned)
    cleaned = _strip_relevant_memories_tags(cleaned)
    cleaned = strip_tool_call_xml_tags(
        cleaned,
        strip_function_calls_xml_payloads=strip_function_calls_xml_payloads,
        strip_function_response_after_plural_tool_calls=strip_function_response_after_plural_tool_calls,
    )
    if strip_internal_trace_lines:
        cleaned = strip_assistant_internal_trace_lines(cleaned)
    cleaned = strip_legacy_bracket_tool_call_blocks(cleaned)
    cleaned = strip_plain_text_tool_call_blocks(cleaned)
    if not preserve_downgraded_tool_text:
        cleaned = strip_downgraded_tool_call_text(cleaned)
    return cleaned


def _apply_assistant_visible_text_stage_pipeline(
    text: str,
    final_trim: ReasoningTagTrim,
    preserve_downgraded_tool_text: bool,
    preserve_minimax_tool_xml: bool,
    strip_function_calls_xml_payloads: bool,
    strip_function_response_after_plural_tool_calls: bool,
    strip_internal_trace_lines: bool,
    reasoning_mode: ReasoningTagMode,
    reasoning_trim: ReasoningTagTrim,
    stage_order: Literal["reasoning-first", "reasoning-last"],
) -> str:
    if not text:
        return text

    if stage_order == "reasoning-first":
        return _apply_final_trim(
            _strip_non_reasoning_stages(
                _strip_reasoning(text, reasoning_mode, reasoning_trim),
                preserve_minimax_tool_xml=preserve_minimax_tool_xml,
                strip_function_calls_xml_payloads=strip_function_calls_xml_payloads,
                strip_function_response_after_plural_tool_calls=strip_function_response_after_plural_tool_calls,
                strip_internal_trace_lines=strip_internal_trace_lines,
                preserve_downgraded_tool_text=preserve_downgraded_tool_text,
            ),
            final_trim=final_trim,
        )

    return _apply_final_trim(
        _strip_reasoning(
            _strip_non_reasoning_stages(
                text,
                preserve_minimax_tool_xml=preserve_minimax_tool_xml,
                strip_function_calls_xml_payloads=strip_function_calls_xml_payloads,
                strip_function_response_after_plural_tool_calls=strip_function_response_after_plural_tool_calls,
                strip_internal_trace_lines=strip_internal_trace_lines,
                preserve_downgraded_tool_text=preserve_downgraded_tool_text,
            ),
            reasoning_mode,
            reasoning_trim,
        ),
        final_trim,
    )


_ASSISTANT_VISIBLE_TEXT_PIPELINE_OPTIONS: dict[
    AssistantVisibleTextSanitizerProfile, dict
] = {
    "delivery": {
        "final_trim": "both",
        "preserve_downgraded_tool_text": False,
        "preserve_minimax_tool_xml": False,
        "strip_function_calls_xml_payloads": False,
        "strip_function_response_after_plural_tool_calls": True,
        "strip_internal_trace_lines": True,
        "reasoning_mode": "strict",
        "reasoning_trim": "both",
        "stage_order": "reasoning-last",
    },
    "history": {
        "final_trim": "none",
        "preserve_downgraded_tool_text": False,
        "preserve_minimax_tool_xml": False,
        "strip_function_calls_xml_payloads": False,
        "strip_function_response_after_plural_tool_calls": False,
        "strip_internal_trace_lines": True,
        "reasoning_mode": "strict",
        "reasoning_trim": "none",
        "stage_order": "reasoning-last",
    },
    "internal-scaffolding": {
        "final_trim": "start",
        "preserve_downgraded_tool_text": True,
        "preserve_minimax_tool_xml": True,
        "strip_function_calls_xml_payloads": False,
        "strip_function_response_after_plural_tool_calls": False,
        "strip_internal_trace_lines": True,
        "reasoning_mode": "preserve",
        "reasoning_trim": "start",
        "stage_order": "reasoning-first",
    },
    "tool-progress": {
        "final_trim": "both",
        "preserve_downgraded_tool_text": False,
        "preserve_minimax_tool_xml": False,
        "strip_function_calls_xml_payloads": True,
        "strip_function_response_after_plural_tool_calls": False,
        "strip_internal_trace_lines": False,
        "reasoning_mode": "strict",
        "reasoning_trim": "both",
        "stage_order": "reasoning-last",
    },
}


def sanitize_assistant_visible_text_with_profile(
    text: str,
    profile: AssistantVisibleTextSanitizerProfile = "delivery",
) -> str:
    options = _ASSISTANT_VISIBLE_TEXT_PIPELINE_OPTIONS[profile]
    return _apply_assistant_visible_text_stage_pipeline(text, **options)


def strip_assistant_internal_scaffolding(text: str) -> str:
    return sanitize_assistant_visible_text_with_profile(text, "internal-scaffolding")


def sanitize_assistant_visible_text(text: str) -> str:
    return sanitize_assistant_visible_text_with_profile(text, "delivery")


def sanitize_assistant_visible_text_with_options(
    text: str,
    trim: Literal["none", "both"] | None = None,
) -> str:
    profile = "history" if trim == "none" else "delivery"
    return sanitize_assistant_visible_text_with_profile(text, profile)
