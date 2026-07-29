"""Support log redaction helpers scrub sensitive fields from diagnostic log payloads.

Mirrors src/logging/diagnostic-support-log-redaction.ts.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openclaw.logging.diagnostic_support_redaction import redact_support_string

LOG_STRING_FIELD_RE = re.compile(
    r"^(?:action|channel|code|component|endpoint|event|handshake|kind|level|localAddr|logger|method|model|module|msg|name|outcome|phase|pluginId|provider|reason|remoteAddr|requestId|runId|service|source|status|subsystem|surface|target|time|traceId|type)$",
    re.IGNORECASE,
)
LOG_SCALAR_FIELD_RE = re.compile(
    r"^(?:active|attempt|bytes|count|durationMs|enabled|exitCode|intervalMs|jobs|limitBytes|localPort|nextWakeAtMs|pid|port|queueDepth|queued|remotePort|statusCode|waitMs|waiting)$",
    re.IGNORECASE,
)
OMITTED_LOG_FIELD_RE = re.compile(
    r"(?:authorization|body|chat|content|cookie|credential|detail|error|header|instruction|message|password|payload|prompt|result|secret|session[-_]?id|session[-_]?key|text|token|tool|transcript|url)",
    re.IGNORECASE,
)
UNSAFE_LOG_MESSAGE_RE = re.compile(
    r"(?:\b(?:ai response|assistant said|chat text|message contents|prompt|raw webhook body|tool output|tool result|transcript|user said|webhook body)\b|auto-responding\b.*:\s*[\"']|partial for\b.*:)",
    re.IGNORECASE,
)
MAX_LOG_STRING_LENGTH = 240
LOGTAPE_META_FIELD = "_meta"
LOGTAPE_ARG_FIELD_RE = re.compile(r"^\d+$")
LOGTAPE_META_STRING_FIELDS = {"logLevelName": "level", "name": "logger"}


def _byte_length(content: str) -> int:
    return len(content.encode("utf-8"))


def _as_optional_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _parse_json_record(value: str) -> dict[str, Any] | None:
    trimmed = value.strip()
    if not trimmed.startswith("{") or not trimmed.endswith("}"):
        return None
    try:
        parsed = json.loads(trimmed)
        return _as_optional_record(parsed)
    except (json.JSONDecodeError, TypeError):
        return None


def _sanitize_log_string(value: str, redaction: dict[str, Any]) -> str:
    return redact_support_string(value, redaction, {"maxLength": MAX_LOG_STRING_LENGTH, "truncationSuffix": ""})


def _is_safe_log_field(key: str, value: Any) -> bool:
    if isinstance(value, str):
        return bool(LOG_STRING_FIELD_RE.match(key))
    return bool(LOG_STRING_FIELD_RE.match(key) or LOG_SCALAR_FIELD_RE.match(key))


def _add_omitted_log_message_metadata(sanitized: dict[str, Any], value: str) -> None:
    sanitized["omitted"] = "log-message"
    sanitized["omittedLogMessageBytes"] = _numeric_log_metadata(sanitized.get("omittedLogMessageBytes")) + _byte_length(value)
    sanitized["omittedLogMessageCount"] = _numeric_log_metadata(sanitized.get("omittedLogMessageCount")) + 1


def _numeric_log_metadata(value: Any) -> int:
    return value if isinstance(value, (int, float)) else 0


def _add_safe_log_field(
    sanitized: dict[str, Any],
    key: str,
    value: Any,
    redaction: dict[str, Any],
) -> None:
    if OMITTED_LOG_FIELD_RE.search(key):
        return
    if not _is_safe_log_field(key, value):
        return
    if isinstance(value, str):
        message = _sanitize_log_string(value, redaction)
        if key == "msg" and (not message or UNSAFE_LOG_MESSAGE_RE.search(message)):
            _add_omitted_log_message_metadata(sanitized, value)
            return
        sanitized[key] = message
    elif isinstance(value, (int, float, bool)) or value is None:
        sanitized[key] = value


def _add_log_object_fields(
    sanitized: dict[str, Any],
    source: dict[str, Any],
    redaction: dict[str, Any],
) -> None:
    for key, value in source.items():
        _add_safe_log_field(sanitized, key, value, redaction)


def _add_log_tape_message_field(
    sanitized: dict[str, Any],
    value: str,
    redaction: dict[str, Any],
) -> None:
    message = _sanitize_log_string(value, redaction)
    if sanitized.get("msg") is None and message and not UNSAFE_LOG_MESSAGE_RE.search(message):
        sanitized["msg"] = message
        return
    _add_omitted_log_message_metadata(sanitized, value)


def sanitize_support_log_record(line: str, redaction: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return {"omitted": "unparsed", "bytes": _byte_length(line)}

    source = _as_optional_record(parsed)
    if source is None:
        return {"omitted": "non-object", "bytes": _byte_length(line)}

    sanitized: dict[str, Any] = {}
    for key, value in source.items():
        if key == LOGTAPE_META_FIELD or LOGTAPE_ARG_FIELD_RE.match(key):
            continue
        _add_safe_log_field(sanitized, key, value, redaction)

    meta = _as_optional_record(source.get(LOGTAPE_META_FIELD))
    if meta:
        for source_key, output_key in LOGTAPE_META_STRING_FIELDS.items():
            if sanitized.get(output_key) is not None:
                continue
            value = meta.get(source_key)
            if isinstance(value, str):
                if source_key == "name":
                    record = _parse_json_record(value)
                    if record:
                        _add_log_object_fields(sanitized, record, redaction)
                        continue
                sanitized[output_key] = _sanitize_log_string(value, redaction)

    args = sorted(
        [(k, v) for k, v in source.items() if LOGTAPE_ARG_FIELD_RE.match(k)],
        key=lambda item: int(item[0]),
    )
    for _, value in args:
        record = _parse_json_record(value) if isinstance(value, str) else _as_optional_record(value)
        if record:
            _add_log_object_fields(sanitized, record, redaction)
            continue
        if isinstance(value, str):
            _add_log_tape_message_field(sanitized, value, redaction)

    if sanitized:
        return sanitized
    return {"omitted": "no-safe-fields", "bytes": _byte_length(line)}


__all__ = ["sanitize_support_log_record"]
