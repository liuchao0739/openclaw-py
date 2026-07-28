from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


from openclaw_extensions.active_memory.config import (
    DEFAULT_PARTIAL_TRANSCRIPT_MAX_CHARS,
    DEFAULT_TRANSCRIPT_READ_MAX_BYTES,
    DEFAULT_TRANSCRIPT_READ_MAX_LINES,
    STRUCTURED_MEMORY_EMPTY_STATUSES,
    STRUCTURED_MEMORY_FAILURE_STATUSES,
)


@dataclass
class TranscriptReadLimits:
    max_chars: int = DEFAULT_PARTIAL_TRANSCRIPT_MAX_CHARS
    max_lines: int = DEFAULT_TRANSCRIPT_READ_MAX_LINES
    max_bytes: int = DEFAULT_TRANSCRIPT_READ_MAX_BYTES


def resolve_transcript_read_limits(limits: dict[str, Any] | None = None) -> TranscriptReadLimits:
    import sys

    def _clamp(val: Any, default: int, min_val: int, max_val: int) -> int:
        try:
            v = int(val) if val is not None else default
        except (ValueError, TypeError):
            v = default
        return max(min_val, min(max_val, v))

    if limits is None:
        limits = {}
    return TranscriptReadLimits(
        max_chars=_clamp(limits.get("maxChars"), DEFAULT_PARTIAL_TRANSCRIPT_MAX_CHARS, 1, DEFAULT_PARTIAL_TRANSCRIPT_MAX_CHARS),
        max_lines=_clamp(limits.get("maxLines"), DEFAULT_TRANSCRIPT_READ_MAX_LINES, 1, DEFAULT_TRANSCRIPT_READ_MAX_LINES),
        max_bytes=_clamp(limits.get("maxBytes"), DEFAULT_TRANSCRIPT_READ_MAX_BYTES, 1, DEFAULT_TRANSCRIPT_READ_MAX_BYTES),
    )


def extract_text_content_parts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content.strip()] if content.strip() else []
    if not isinstance(content, list):
        return []
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        if "text" in item and isinstance(item["text"], str):
            parts.append(item["text"])
            continue
        if item.get("type") == "text" and isinstance(item.get("content"), str):
            parts.append(item["content"])
    return [p.strip() for p in parts if p.strip()]


def extract_text_content(content: Any) -> str:
    return " ".join(extract_text_content_parts(content)).strip()


def _as_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


@dataclass
class ActiveMemorySearchDebug:
    backend: str | None = None
    configured_mode: str | None = None
    effective_mode: str | None = None
    fallback: str | None = None
    search_ms: int | None = None
    hits: int | None = None
    warning: str | None = None
    action: str | None = None
    error: str | None = None


def extract_active_memory_search_debug_from_session_record(value: Any) -> ActiveMemorySearchDebug | None:
    record = _as_record(value)
    if record is None:
        return None
    nested_message = _as_record(record.get("message"))
    record_tool_name = _normalize_lowercase_string_or_empty(record.get("toolName"))
    top_level_message = None
    if record.get("role") == "toolResult" or record_tool_name in ("memory_search", "memory_recall"):
        top_level_message = record
    message = nested_message or top_level_message
    if message is None:
        return None
    role = _normalize_optional_string(message.get("role"))
    tool_name = _normalize_lowercase_string_or_empty(message.get("toolName"))
    if role != "toolResult" or tool_name not in ("memory_search", "memory_recall"):
        return None
    details = _as_record(message.get("details"))
    debug = _as_record(details.get("debug")) if details else None
    warning = _normalize_optional_string(details.get("warning")) if details else None
    action = _normalize_optional_string(details.get("action")) if details else None
    error = _normalize_optional_string(details.get("error")) if details else None
    if debug is None and warning is None and action is None and error is None:
        return None
    search_ms = None
    hits = None
    if debug is not None:
        raw_search_ms = debug.get("searchMs")
        if isinstance(raw_search_ms, (int, float)) and float(raw_search_ms) == float(raw_search_ms):
            search_ms = int(raw_search_ms)
        raw_hits = debug.get("hits")
        if isinstance(raw_hits, (int, float)) and float(raw_hits) == float(raw_hits):
            hits = int(raw_hits)
    return ActiveMemorySearchDebug(
        backend=_normalize_optional_string(debug.get("backend")) if debug else None,
        configured_mode=_normalize_optional_string(debug.get("configuredMode")) if debug else None,
        effective_mode=_normalize_optional_string(debug.get("effectiveMode")) if debug else None,
        fallback=_normalize_optional_string(debug.get("fallback")) if debug else None,
        search_ms=search_ms,
        hits=hits,
        warning=warning,
        action=action,
        error=error,
    )


def extract_tool_result_name_from_session_record(value: Any) -> str | None:
    record = _as_record(value)
    if record is None:
        return None
    nested_message = _as_record(record.get("message"))
    top_level_message = record if record.get("role") == "toolResult" else None
    message = nested_message or top_level_message
    if message is None:
        return None
    role = _normalize_optional_string(message.get("role"))
    tool_name = _normalize_lowercase_string_or_empty(message.get("toolName"))
    return tool_name if role == "toolResult" and tool_name else None


def _read_explicit_memory_evidence(source: dict[str, Any]) -> bool | None:
    status_val = source.get("status")
    status = None
    if isinstance(status_val, str):
        status = status_val.strip().lower().replace(" ", "_").replace("-", "_")
    if status is not None and status in STRUCTURED_MEMORY_EMPTY_STATUSES:
        return False
    result_collections = [source.get("results"), source.get("memories"), source.get("items")]
    if any(isinstance(entry, list) for entry in result_collections):
        return any(isinstance(entry, list) and len(entry) > 0 for entry in result_collections)
    result_counts = [
        source.get("count"), source.get("matches"), source.get("memoryCount"),
        source.get("resultCount"), source.get("totalMatches"),
    ]
    numeric_counts = [float(c) for c in result_counts if isinstance(c, (int, float))]
    if numeric_counts:
        return any(c > 0 for c in numeric_counts)
    if "found" in source:
        return source.get("found") is True
    if "hasResults" in source:
        return source.get("hasResults") is True
    return None


def _read_structured_memory_failure(source: Any) -> bool | None:
    record = _as_record(source)
    if record is None:
        return None
    status_val = record.get("status")
    status = None
    if isinstance(status_val, str):
        status = status_val.strip().lower().replace(" ", "_").replace("-", "_")
    has_failure_status = status is not None and status in STRUCTURED_MEMORY_FAILURE_STATUSES
    has_failure_fields = has_failure_status or any(
        key in record for key in ["disabled", "unavailable", "success", "error"]
    )
    if not has_failure_fields:
        return None
    return (
        has_failure_status
        or record.get("disabled") is True
        or record.get("unavailable") is True
        or record.get("success") is False
        or bool(record.get("error"))
    )


def _read_structured_memory_evidence(source: Any) -> bool | None:
    if isinstance(source, list):
        return len(source) > 0
    record = _as_record(source)
    if record is not None:
        return _read_explicit_memory_evidence(record)
    return None


def _read_structured_content_state(
    content: Any,
    read_state: Callable[[Any], bool | None],
    decisive_state: bool,
) -> bool | None:
    parts = extract_text_content_parts(content)
    saw_other_state = False
    for part in parts:
        try:
            state = read_state(json.loads(part))
            if state == decisive_state:
                return decisive_state
            if state == (not decisive_state):
                saw_other_state = True
        except (json.JSONDecodeError, ValueError):
            pass
    try:
        state = read_state(json.loads(" ".join(parts).strip()))
        if state is not None:
            return state
    except (json.JSONDecodeError, ValueError):
        pass
    return (not decisive_state) if saw_other_state else None


def _read_structured_memory_failure_from_content(content: Any) -> bool | None:
    return _read_structured_content_state(content, _read_structured_memory_failure, True)


def _read_structured_memory_evidence_from_content(content: Any) -> bool | None:
    return _read_structured_content_state(content, _read_structured_memory_evidence, False)


def has_usable_memory_result_in_session_record(
    value: Any,
    tools_allow: list[str] | None = None,
) -> bool:
    from openclaw_extensions.active_memory.config import (
        DEFAULT_ACTIVE_MEMORY_TOOLS_ALLOW,
        LANCEDB_ACTIVE_MEMORY_TOOLS_ALLOW,
    )
    if tools_allow is None:
        tools_allow = list(DEFAULT_ACTIVE_MEMORY_TOOLS_ALLOW) + list(LANCEDB_ACTIVE_MEMORY_TOOLS_ALLOW)
    record = _as_record(value)
    if record is None:
        return False
    nested_message = _as_record(record.get("message"))
    record_tool_name = _normalize_lowercase_string_or_empty(record.get("toolName"))
    top_level_message = None
    if record.get("role") == "toolResult" or record_tool_name in ("memory_search", "memory_recall"):
        top_level_message = record
    message = nested_message or top_level_message
    if message is None:
        return False
    if _normalize_optional_string(message.get("role")) != "toolResult":
        return False
    tool_name = _normalize_lowercase_string_or_empty(message.get("toolName"))
    if not tool_name or tool_name not in tools_allow:
        return False
    if has_unavailable_memory_result_in_session_record(value, tools_allow):
        return False
    details = _as_record(message.get("details"))
    content_str = extract_text_content(message.get("content"))
    if tool_name == "memory_search":
        if details is not None and isinstance(details.get("results"), list):
            return len(details["results"]) > 0
        import re
        return bool(re.search(r'"results"\s*:\s*\[\s*([^\s\]])', content_str))
    if tool_name == "memory_recall":
        if details is not None and isinstance(details.get("memories"), list):
            return len(details["memories"]) > 0
        import re
        return bool(re.search(r"^Found [1-9]\d* memories:", content_str))
    if tool_name == "memory_get":
        text_val = _normalize_optional_string(details.get("text")) if details else None
        if text_val is not None:
            return len(text_val) > 0
        import re
        return bool(re.search(r'"text"\s*:\s*"(?!")', content_str))
    if tool_name == "lcm_grep":
        if details is not None:
            total = details.get("totalMatches")
            if isinstance(total, (int, float)) and float(total) == float(total) and total > 0:
                return True
        import re
        return bool(re.search(r"## LCM Grep Results[\s\S]*\*\*Total matches:\*\*\s+[1-9]\d*$", content_str, re.MULTILINE))
    if tool_name == "lcm_describe":
        if details is not None:
            type_val = _normalize_optional_string(details.get("type"))
            id_val = _normalize_optional_string(details.get("id"))
            if id_val and type_val in ("summary", "file"):
                return True
        import re
        return bool(re.search(r"LCM_SUMMARY \S+", content_str)) or bool(re.search(r"## LCM File: \S+", content_str))
    if tool_name == "lcm_expand_query":
        if details is not None:
            expanded = details.get("expandedSummaryCount")
            if isinstance(expanded, (int, float)) and float(expanded) == float(expanded) and expanded > 0:
                answer_val = _normalize_optional_string(details.get("answer"))
                if answer_val:
                    return True
        try:
            parsed = json.loads(content_str)
            if isinstance(parsed, dict):
                expanded = parsed.get("expandedSummaryCount")
                if isinstance(expanded, (int, float)) and float(expanded) == float(expanded) and expanded > 0:
                    answer_val = _normalize_optional_string(parsed.get("answer"))
                    if answer_val:
                        return True
        except (json.JSONDecodeError, ValueError):
            pass
        return False
    normalized_content = _normalize_optional_string(content_str)
    explicit_evidence = _read_explicit_memory_evidence(details) if details is not None else None
    structured_evidence = _read_structured_memory_evidence_from_content(message.get("content")) if normalized_content else None
    return bool(normalized_content) and explicit_evidence is not False and structured_evidence is not False


def has_unavailable_memory_result_in_session_record(
    value: Any,
    tools_allow: list[str] | None = None,
) -> bool:
    from openclaw_extensions.active_memory.config import (
        DEFAULT_ACTIVE_MEMORY_TOOLS_ALLOW,
        LANCEDB_ACTIVE_MEMORY_TOOLS_ALLOW,
    )
    if tools_allow is None:
        tools_allow = list(DEFAULT_ACTIVE_MEMORY_TOOLS_ALLOW) + list(LANCEDB_ACTIVE_MEMORY_TOOLS_ALLOW)
    record = _as_record(value)
    if record is None:
        return False
    nested_message = _as_record(record.get("message"))
    top_level_message = record if record.get("role") == "toolResult" else None
    message = nested_message or top_level_message
    if message is None:
        return False
    if _normalize_optional_string(message.get("role")) != "toolResult":
        return False
    tool_name = _normalize_lowercase_string_or_empty(message.get("toolName"))
    if not tool_name or tool_name not in tools_allow:
        return False
    details = _as_record(message.get("details"))
    unavailable = message.get("isError") is True or _read_structured_memory_failure(details) is True
    if unavailable:
        return True
    return _read_structured_memory_failure_from_content(message.get("content")) is True


def has_terminal_unavailable_memory_result_in_session_record(
    value: Any,
    tools_allow: list[str],
) -> bool:
    record = _as_record(value)
    if record is None:
        return False
    nested_message = _as_record(record.get("message"))
    top_level_message = record if record.get("role") == "toolResult" else None
    message = nested_message or top_level_message
    if message is None:
        return False
    if _normalize_optional_string(message.get("role")) != "toolResult":
        return False
    tool_name = _normalize_lowercase_string_or_empty(message.get("toolName"))
    if not tool_name or tool_name not in tools_allow:
        return False
    details = _as_record(message.get("details"))
    if details is not None and (details.get("disabled") is True or details.get("unavailable") is True):
        return True
    status_val = details.get("status") if details else None
    status = None
    if isinstance(status_val, str):
        status = status_val.strip().lower().replace(" ", "_").replace("-", "_")
    if status in ("disabled", "unavailable"):
        return True
    if tool_name not in ("memory_search", "memory_recall"):
        return False
    debug = extract_active_memory_search_debug_from_session_record(value)
    return bool(debug and debug.error) or bool(details and details.get("error"))


def stream_bounded_transcript_jsonl(
    session_file: str,
    on_record: Callable[[Any], bool | None],
    limits: TranscriptReadLimits | None = None,
) -> None:
    resolved_limits = limits or TranscriptReadLimits()
    path = Path(session_file)
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size > resolved_limits.max_bytes:
            return
    except OSError:
        return
    seen_lines = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                seen_lines += 1
                if seen_lines > resolved_limits.max_lines:
                    break
                trimmed = line.strip()
                if not trimmed:
                    continue
                try:
                    record = json.loads(trimmed)
                    result = on_record(record)
                    if result is True:
                        break
                except (json.JSONDecodeError, ValueError):
                    pass
    except (OSError, UnicodeDecodeError):
        pass


async def read_active_memory_transcript_state(
    session_file: str,
    limits: TranscriptReadLimits | None = None,
    tools_allow: list[str] | None = None,
) -> dict[str, Any]:
    search_debug: ActiveMemorySearchDebug | None = None
    has_usable_memory_result = False
    has_unavailable_memory_search_result = False

    def _on_record(record: Any) -> bool:
        nonlocal search_debug, has_usable_memory_result, has_unavailable_memory_search_result
        debug = extract_active_memory_search_debug_from_session_record(record)
        if debug is not None:
            search_debug = debug
        has_unavailable_memory_search_result = has_unavailable_memory_search_result or has_unavailable_memory_result_in_session_record(record, tools_allow)
        has_usable_memory_result = has_usable_memory_result or has_usable_memory_result_in_session_record(record, tools_allow)
        return False

    stream_bounded_transcript_jsonl(session_file, _on_record, limits)
    return {
        "search_debug": search_debug,
        "has_usable_memory_result": has_usable_memory_result,
        "has_unavailable_memory_search_result": has_unavailable_memory_search_result,
    }


async def read_active_memory_search_debug(
    session_file: str,
    limits: TranscriptReadLimits | None = None,
) -> ActiveMemorySearchDebug | None:
    state = await read_active_memory_transcript_state(session_file, limits)
    return state.get("search_debug")


async def read_merged_active_memory_transcript_state(
    session_files: list[str],
    tools_allow: list[str],
) -> dict[str, Any]:
    search_debug: ActiveMemorySearchDebug | None = None
    has_usable_memory_result = False
    has_unavailable_memory_search_result = False
    seen_files: set[str] = set()
    for session_file in session_files:
        if session_file in seen_files:
            continue
        seen_files.add(session_file)
        state = await read_active_memory_transcript_state(session_file, None, tools_allow)
        if state.get("search_debug") is not None:
            search_debug = state.get("search_debug")
        has_usable_memory_result = has_usable_memory_result or state.get("has_usable_memory_result", False)
        has_unavailable_memory_search_result = has_unavailable_memory_search_result or state.get("has_unavailable_memory_search_result", False)
    return {
        "search_debug": search_debug,
        "has_usable_memory_result": has_usable_memory_result,
        "has_unavailable_memory_search_result": has_unavailable_memory_search_result,
    }


async def read_partial_assistant_text(
    session_file: str | None,
    limits: TranscriptReadLimits | None = None,
) -> str | None:
    if session_file is None:
        return None
    texts: list[str] = []
    resolved_limits = limits or TranscriptReadLimits()
    collected_chars = 0

    def _on_record(record: Any) -> bool:
        nonlocal collected_chars
        text = extract_assistant_text_from_session_record(record)
        if not text:
            return False
        separator_chars = 1 if texts else 0
        remaining = resolved_limits.max_chars - collected_chars - separator_chars
        if remaining <= 0:
            return True
        next_text = text[:remaining]
        texts.append(next_text)
        collected_chars += separator_chars + len(next_text)
        return collected_chars >= resolved_limits.max_chars

    stream_bounded_transcript_jsonl(session_file, _on_record, resolved_limits)
    joined = "\n".join(t.strip() for t in texts if t.strip())
    return joined[:resolved_limits.max_chars].strip() or None


def extract_assistant_text_from_session_record(value: Any) -> str:
    record = _as_record(value)
    if record is None:
        return ""
    nested_message = _as_record(record.get("message"))
    top_level_message = record if _normalize_optional_string(record.get("role")) == "assistant" else None
    message = nested_message or top_level_message
    if message is None:
        return ""
    if _normalize_optional_string(message.get("role")) != "assistant":
        return ""
    return extract_text_content(message.get("content")).strip()


def normalize_search_debug(value: Any) -> ActiveMemorySearchDebug | None:
    debug = _as_record(value)
    if debug is None:
        return None
    search_ms = None
    hits = None
    raw_search_ms = debug.get("searchMs")
    if isinstance(raw_search_ms, (int, float)) and float(raw_search_ms) == float(raw_search_ms):
        search_ms = int(raw_search_ms)
    raw_hits = debug.get("hits")
    if isinstance(raw_hits, (int, float)) and float(raw_hits) == float(raw_hits):
        hits = int(raw_hits)
    normalized = ActiveMemorySearchDebug(
        backend=_normalize_optional_string(debug.get("backend")),
        configured_mode=_normalize_optional_string(debug.get("configuredMode")),
        effective_mode=_normalize_optional_string(debug.get("effectiveMode")),
        fallback=_normalize_optional_string(debug.get("fallback")),
        search_ms=search_ms,
        hits=hits,
        warning=_normalize_optional_string(debug.get("warning")) or _normalize_optional_string(debug.get("reason")),
        action=_normalize_optional_string(debug.get("action")),
        error=_normalize_optional_string(debug.get("error")),
    )
    if (
        normalized.backend
        or normalized.configured_mode
        or normalized.effective_mode
        or normalized.fallback
        or isinstance(normalized.search_ms, int)
        or isinstance(normalized.hits, int)
        or normalized.warning
        or normalized.action
        or normalized.error
    ):
        return normalized
    return None


def read_active_memory_search_debug_from_run_result(result: Any) -> ActiveMemorySearchDebug | None:
    record = _as_record(result)
    if record is None:
        return None
    meta = _as_record(record.get("meta"))
    return (
        normalize_search_debug(meta.get("activeMemorySearchDebug") if meta else None)
        or normalize_search_debug(meta.get("memorySearchDebug") if meta else None)
        or normalize_search_debug(record.get("activeMemorySearchDebug"))
        or normalize_search_debug(record.get("memorySearchDebug"))
    )


def read_active_memory_session_file_from_run_result(result: Any) -> str | None:
    record = _as_record(result)
    if record is None:
        return None
    meta = _as_record(record.get("meta"))
    if meta is None:
        return None
    agent_meta = _as_record(meta.get("agentMeta"))
    return (
        _normalize_optional_string(agent_meta.get("sessionFile")) if agent_meta else None
        or _normalize_optional_string(meta.get("sessionFile"))
    )


def read_memory_tool_result_evidence(
    tool_name: str,
    result: Any,
    is_error: bool,
    tools_allow: list[str],
) -> dict[str, bool]:
    result_record = _as_record(result)
    if result_record is None:
        return {"has_usable_memory_result": False, "has_unavailable_memory_search_result": False}
    raw_content = result_record.get("content")
    detailed_content = _normalize_optional_string(result_record.get("detailedContent"))
    text_content = detailed_content
    if text_content is None and isinstance(raw_content, str):
        text_content = _normalize_optional_string(raw_content)
    if text_content is None:
        text_content = ""
    record = {
        "message": {
            "role": "toolResult",
            "toolName": tool_name,
            "isError": is_error,
            "content": raw_content if isinstance(raw_content, list) else (
                [{"type": "text", "text": text_content}] if text_content else []
            ),
            "details": result_record.get("details"),
        },
    }
    return {
        "has_usable_memory_result": has_usable_memory_result_in_session_record(record, tools_allow),
        "has_unavailable_memory_search_result": has_unavailable_memory_result_in_session_record(record, tools_allow),
    }


async def read_terminal_memory_search_result(
    session_file: str,
    limits: TranscriptReadLimits | None = None,
    tools_allow: list[str] | None = None,
) -> dict[str, Any] | None:
    if tools_allow is None:
        tools_allow = []
    recall_path_names = {
        _normalize_lowercase_string_or_empty(t)
        for t in tools_allow
        if _normalize_lowercase_string_or_empty(t) and _normalize_lowercase_string_or_empty(t) != "memory_get"
    }
    if not recall_path_names:
        return None
    unavailable_path_names: set[str] = set()
    has_usable_memory_result = False
    search_debug: ActiveMemorySearchDebug | None = None

    def _on_record(record: Any) -> bool:
        nonlocal has_usable_memory_result, search_debug
        has_usable_memory_result = has_usable_memory_result or has_usable_memory_result_in_session_record(record, tools_allow)
        debug = extract_active_memory_search_debug_from_session_record(record)
        if debug is not None:
            search_debug = debug
        tool_name = extract_tool_result_name_from_session_record(record)
        if not tool_name or tool_name not in recall_path_names:
            return False
        if has_terminal_unavailable_memory_result_in_session_record(record, tools_allow):
            unavailable_path_names.add(tool_name)
        else:
            unavailable_path_names.discard(tool_name)
        return False

    stream_bounded_transcript_jsonl(session_file, _on_record, limits)
    if len(unavailable_path_names) != len(recall_path_names):
        return None
    return {
        "status": "unavailable",
        "has_usable_memory_result": has_usable_memory_result,
        "search_debug": search_debug,
    }