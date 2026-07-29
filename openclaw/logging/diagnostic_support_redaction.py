"""Diagnostic support redaction helpers scrub support bundle files and paths.

Mirrors src/logging/diagnostic-support-redaction.ts.
"""

from __future__ import annotations

import os
import re
from typing import Any

from openclaw.logging.redact import redact_sensitive_text

SECRET_SUPPORT_FIELD_RE = re.compile(r"(?:authorization|cookie|credential|key|password|passwd|secret|token)", re.IGNORECASE)
PAYLOAD_SUPPORT_FIELD_RE = re.compile(r"(?:body|chat|content|detail|error|header|instruction|message|payload|prompt|result|text|tool|transcript)", re.IGNORECASE)
IDENTIFIER_SUPPORT_FIELD_RE = re.compile(r"(?:account[-_]?id|chat[-_]?id|conversation[-_]?id|email|message[-_]?id|phone|thread[-_]?id|user[-_]?id|username)", re.IGNORECASE)
PRIVATE_MAP_SUPPORT_FIELD_RE = re.compile(r"^(?:accounts|chats|conversations|messages|threads|users)$", re.IGNORECASE)
CONFIG_PRIVATE_FIELD_RE = re.compile(r"(?:allow[-_]?from|allow[-_]?to|deny[-_]?from|deny[-_]?to|blocked[-_]?from|blocked[-_]?users|owner[-_]?id|sender[-_]?id|recipient[-_]?id)", re.IGNORECASE)
SENSITIVE_COMMAND_ARG_RE = re.compile(r"^--(?:api[-_]?key|hook[-_]?token|password|password-file|passwd|secret|token)(?:=.*)?$", re.IGNORECASE)
BASIC_AUTH_RE = re.compile(r"\bBasic\s+[A-Za-z0-9+/]+={0,2}", re.IGNORECASE)
COOKIE_HEADER_RE = re.compile(r"\b(Cookie|Set-Cookie)\s*:\s*[^\r\n]+", re.IGNORECASE)
AWS_ACCESS_KEY_ID_RE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
URL_USERINFO_RE = re.compile(r"\b([a-z][a-z0-9+.-]*:\/\/)([^/@\s:?#]+)(?::([^/@\s?#]+))?@", re.IGNORECASE)
URL_PARAM_RE = re.compile(r"([?&])([^=&\s]+)=([^&#\s]+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
MATRIX_USER_ID_RE = re.compile(r"@[A-Za-z0-9._=-]+:[A-Za-z0-9.-]+")
MATRIX_ROOM_ID_RE = re.compile(r"![A-Za-z0-9._=-]+:[A-Za-z0-9.-]+")
MATRIX_EVENT_ID_RE = re.compile(r"\$[A-Za-z0-9_-]{16,}")
HANDLE_RE = re.compile(r"(^|[^\w:/])@[A-Za-z0-9_]{5,}\b(?!\.)")
LONG_DECIMAL_ID_RE = re.compile(r"\b\d{9,}\b")
MAX_SUPPORT_STRING_LENGTH = 2000
MAX_SUPPORT_SNAPSHOT_DEPTH = 10
MAX_SUPPORT_ARRAY_ITEMS = 1000
MAX_SUPPORT_OBJECT_ENTRIES = 1000
DEFAULT_TRUNCATION_SUFFIX = "...<truncated>"
TRUNCATED_SUPPORT_FIELD = "<truncated>"


def _is_private_support_field(key: str) -> bool:
    return bool(SECRET_SUPPORT_FIELD_RE.search(key) or PAYLOAD_SUPPORT_FIELD_RE.search(key) or IDENTIFIER_SUPPORT_FIELD_RE.search(key))


def _is_private_config_field(key: str) -> bool:
    return _is_private_support_field(key) or bool(CONFIG_PRIVATE_FIELD_RE.search(key))


def _is_windows_absolute_path(value: str) -> bool:
    return bool(re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", value))


def _normalize_path_prefix(value: str) -> str:
    if _is_windows_absolute_path(value):
        return os.path.normpath(value)
    return os.path.abspath(value)


def _add_path_prefix(prefixes: dict[str, dict[str, Any]], prefix: str, label: str, case_insensitive: bool) -> None:
    if prefix not in prefixes:
        prefixes[prefix] = {"prefix": prefix, "label": label, "caseInsensitive": case_insensitive}


def _add_path_prefix_variants(prefixes: dict[str, dict[str, Any]], value: str | None, label: str) -> None:
    if not value:
        return
    normalized = _normalize_path_prefix(value)
    case_insensitive = _is_windows_absolute_path(normalized)
    _add_path_prefix(prefixes, normalized, label, case_insensitive)
    if _is_windows_absolute_path(normalized):
        _add_path_prefix(prefixes, normalized.replace("\\", "/"), label, case_insensitive)


def _path_redaction_prefixes(options: dict[str, Any]) -> list[dict[str, Any]]:
    prefixes: dict[str, dict[str, Any]] = {}
    _add_path_prefix_variants(prefixes, options.get("stateDir"), "$OPENCLAW_STATE_DIR")
    env = options.get("env") or {}
    _add_path_prefix_variants(prefixes, env.get("HOME"), "~")
    _add_path_prefix_variants(prefixes, env.get("USERPROFILE"), "~")
    return sorted(prefixes.values(), key=lambda p: len(p["prefix"]), reverse=True)


def _match_path_prefix(file_path: str, prefix: dict[str, Any]) -> str | None:
    prefix_str = prefix["prefix"]
    has_prefix = (
        file_path.lower().startswith(prefix_str.lower())
        if prefix["caseInsensitive"]
        else file_path.startswith(prefix_str)
    )
    if len(file_path) == len(prefix_str) and has_prefix:
        return ""
    if not has_prefix:
        return None
    next_char = file_path[len(prefix_str)] if len(file_path) > len(prefix_str) else None
    if next_char in ("/", "\\"):
        return file_path[len(prefix_str):]
    return None


def _is_support_absolute_path(value: str) -> bool:
    return os.path.isabs(value) or _is_windows_absolute_path(value)


def redact_path_for_support(file: str | None, options: dict[str, Any]) -> str:
    if file is None or not isinstance(file, str):
        return ""
    if file.startswith("$"):
        return file
    candidates = [os.path.abspath(file)] if not _is_windows_absolute_path(file) else [os.path.normpath(file), file.replace("\\", "/")]
    for next_path in candidates:
        for prefix in _path_redaction_prefixes(options):
            suffix = _match_path_prefix(next_path, prefix)
            if suffix is not None:
                return f"{prefix['label']}{suffix}"
    return redact_sensitive_text(candidates[0] if candidates else file, {"mode": "tools"})


def _replace_known_path_prefix(value: str, prefix: dict[str, Any]) -> str:
    search = prefix["prefix"].lower() if prefix["caseInsensitive"] else prefix["prefix"]
    haystack = value.lower() if prefix["caseInsensitive"] else value
    offset = 0
    next_str = ""
    while offset < len(value):
        index = haystack.find(search, offset)
        if index == -1:
            next_str += value[offset:]
            break
        next_str += value[offset:index]
        next_str += prefix["label"]
        offset = index + len(prefix["prefix"])
    return next_str


def _redact_known_path_prefixes_for_support(value: str, redaction: dict[str, Any]) -> str:
    next_str = value
    for prefix in _path_redaction_prefixes(redaction):
        next_str = _replace_known_path_prefix(next_str, prefix)
    return next_str


def redact_text_for_support(value: str) -> str:
    redacted = redact_sensitive_text(value, {"mode": "tools"})
    redacted = BASIC_AUTH_RE.sub("Basic <redacted>", redacted)
    redacted = COOKIE_HEADER_RE.sub(r"\1: <redacted>", redacted)
    redacted = AWS_ACCESS_KEY_ID_RE.sub("<redacted-aws-key>", redacted)
    redacted = JWT_RE.sub("<redacted-jwt>", redacted)
    redacted = URL_USERINFO_RE.sub(
        lambda m: f"{m.group(1)}<redacted>:<redacted>@" if m.group(3) else f"{m.group(1)}<redacted>@",
        redacted,
    )
    redacted = EMAIL_RE.sub("<redacted-email>", redacted)
    redacted = HANDLE_RE.sub(r"\1<redacted-handle>", redacted)
    redacted = MATRIX_USER_ID_RE.sub("<redacted-matrix-user>", redacted)
    redacted = MATRIX_ROOM_ID_RE.sub("<redacted-matrix-room>", redacted)
    redacted = MATRIX_EVENT_ID_RE.sub("<redacted-matrix-event>", redacted)
    redacted = LONG_DECIMAL_ID_RE.sub("<redacted-id>", redacted)
    return redacted


def redact_support_string(
    value: str,
    redaction: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> str:
    opts = options or {}
    max_length = opts.get("maxLength", MAX_SUPPORT_STRING_LENGTH)
    truncation_suffix = opts.get("truncationSuffix", DEFAULT_TRUNCATION_SUFFIX)
    redacted = redact_text_for_support(value)
    if _is_support_absolute_path(redacted):
        path_redacted = redact_path_for_support(redacted, redaction)
    else:
        path_redacted = _redact_known_path_prefixes_for_support(redacted, redaction)
    if len(path_redacted) <= max_length:
        return path_redacted
    return path_redacted[:max_length] + truncation_suffix


def _sanitize_command_arguments(args: list[Any], redaction: dict[str, Any]) -> list[Any]:
    redact_next = False
    result = []
    for arg in args:
        if not isinstance(arg, str):
            result.append(sanitize_support_snapshot_value(arg, redaction))
            continue
        if redact_next:
            redact_next = False
            result.append("<redacted>")
            continue
        if SENSITIVE_COMMAND_ARG_RE.match(arg):
            has_inline_value = "=" in arg
            if not has_inline_value:
                redact_next = True
            result.append(re.sub(r"[=].*", "=<redacted>", arg) if has_inline_value else arg)
            continue
        result.append(redact_support_string(arg, redaction))
    return result


def _limited_support_array(value: list[Any]) -> dict[str, Any]:
    return {"count": len(value), "items": value[:MAX_SUPPORT_ARRAY_ITEMS]}


def _support_array_result(items: list[Any], count: int) -> Any:
    if count <= MAX_SUPPORT_ARRAY_ITEMS:
        return items
    return {"items": items, "truncated": True, "count": count, "limit": MAX_SUPPORT_ARRAY_ITEMS}


def _add_truncation_metadata(sanitized: dict[str, Any], count: int) -> None:
    if count > MAX_SUPPORT_OBJECT_ENTRIES:
        sanitized[TRUNCATED_SUPPORT_FIELD] = {"truncated": True, "count": count, "limit": MAX_SUPPORT_OBJECT_ENTRIES}


def _as_optional_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def sanitize_support_snapshot_value(
    value: Any,
    redaction: dict[str, Any],
    key: str = "",
    depth: int = 0,
) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return "<redacted>" if _is_private_support_field(key) else value
    if isinstance(value, str):
        return "<redacted>" if _is_private_support_field(key) else redact_support_string(value, redaction)
    if depth >= MAX_SUPPORT_SNAPSHOT_DEPTH:
        return "<truncated>"
    if isinstance(value, list):
        limited = _limited_support_array(value)
        if key == "programArguments":
            return _support_array_result(_sanitize_command_arguments(limited["items"], redaction), limited["count"])
        return _support_array_result(
            [sanitize_support_snapshot_value(entry, redaction, key, depth + 1) for entry in limited["items"]],
            limited["count"],
        )
    record = _as_optional_record(value)
    if record is None:
        return "<unsupported>"
    if PRIVATE_MAP_SUPPORT_FIELD_RE.match(key):
        return {"count": len(record)}
    sanitized: dict[str, Any] = {}
    sorted_entries = sorted(record.items())
    count = len(sorted_entries)
    for entry_key, entry_value in sorted_entries[:MAX_SUPPORT_OBJECT_ENTRIES]:
        sanitized[entry_key] = (
            "<redacted>"
            if _is_private_support_field(entry_key)
            else sanitize_support_snapshot_value(entry_value, redaction, entry_key, depth + 1)
        )
    _add_truncation_metadata(sanitized, count)
    return sanitized


def sanitize_support_config_value(
    value: Any,
    redaction: dict[str, Any],
    key: str = "",
    depth: int = 0,
) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return "<redacted>" if _is_private_config_field(key) else value
    if isinstance(value, str):
        return "<redacted>" if _is_private_config_field(key) else redact_support_string(value, redaction)
    if depth >= MAX_SUPPORT_SNAPSHOT_DEPTH:
        return "<truncated>"
    if isinstance(value, list):
        if _is_private_config_field(key):
            return {"redacted": True, "count": len(value)}
        limited = _limited_support_array(value)
        return _support_array_result(
            [sanitize_support_config_value(entry, redaction, key, depth + 1) for entry in limited["items"]],
            limited["count"],
        )
    record = _as_optional_record(value)
    if record is None:
        return "<unsupported>"
    if _is_private_config_field(key):
        if record.get("source") is not None or record.get("provider") is not None:
            sanitized: dict[str, Any] = {}
            if isinstance(record.get("source"), str):
                sanitized["source"] = record["source"]
            if isinstance(record.get("provider"), str):
                sanitized["provider"] = record["provider"]
            sanitized["id"] = "<redacted>"
            return sanitized
        return "<redacted>"
    sanitized = {}
    redact_entry_keys = bool(PRIVATE_MAP_SUPPORT_FIELD_RE.match(key))
    private_entry_label = key.lower().rstrip("s") if redact_entry_keys else ""
    private_entry_index = 0
    sorted_entries = sorted(record.items())
    count = len(sorted_entries)
    for entry_key, entry_value in sorted_entries[:MAX_SUPPORT_OBJECT_ENTRIES]:
        output_key = entry_key
        if redact_entry_keys:
            private_entry_index += 1
            output_key = f"<redacted-{private_entry_label}-{private_entry_index}>"
        sanitized[output_key] = sanitize_support_config_value(entry_value, redaction, entry_key, depth + 1)
    _add_truncation_metadata(sanitized, count)
    return sanitized


__all__ = [
    "redact_path_for_support",
    "redact_text_for_support",
    "redact_support_string",
    "sanitize_support_snapshot_value",
    "sanitize_support_config_value",
]
