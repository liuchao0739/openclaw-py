from __future__ import annotations

import json
from typing import Any, Optional


def extract_error_code(err: Any) -> str | None:
    if not err or not isinstance(err, object):
        return None
    code = getattr(err, "code", None)
    if isinstance(code, str):
        return code
    if isinstance(code, int):
        return str(code)
    return None


def read_error_name(err: Any) -> str:
    if not err or not isinstance(err, object):
        return ""
    name = getattr(err, "name", None)
    return name if isinstance(name, str) else ""


def collect_error_graph_candidates(
    err: Any,
    resolve_nested: Any = None,
) -> list[Any]:
    queue: list[Any] = [err]
    seen: set[Any] = set()
    candidates: list[Any] = []
    while queue:
        current = queue.pop(0)
        if current is None or current in seen:
            continue
        seen.add(current)
        candidates.append(current)
        if not current or not isinstance(current, dict) or not resolve_nested:
            continue
        for nested in resolve_nested(current):
            if nested is not None and nested not in seen:
                queue.append(nested)
    return candidates


def is_errno(err: Any) -> bool:
    return bool(err and isinstance(err, object) and hasattr(err, "code"))


def has_errno_code(err: Any, code: str) -> bool:
    return is_errno(err) and getattr(err, "code", None) == code


def format_error_message(err: Any) -> str:
    formatted: str
    if isinstance(err, Exception):
        formatted = err.message or err.name or "Error"
        cause = err.__cause__
        seen: set[Any] = {err}
        seen_messages: set[str] = {formatted}

        def append_cause_message(message: str) -> None:
            if not message or message in seen_messages:
                return
            nonlocal formatted
            formatted += f" | {message}"
            seen_messages.add(message)

        while cause and cause not in seen:
            seen.add(cause)
            if isinstance(cause, Exception):
                append_cause_message(cause.message or "")
                code = extract_error_code(cause)
                if code:
                    append_cause_message(code)
                cause = cause.__cause__
            elif isinstance(cause, str):
                append_cause_message(cause)
                break
            else:
                break
    elif isinstance(err, str):
        formatted = err
    elif isinstance(err, (int, float, bool)):
        formatted = str(err)
    else:
        try:
            formatted = json.dumps(err)
        except (TypeError, ValueError):
            formatted = str(err)
    return formatted


def stringify_non_error_cause(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value) or str(value)
    except (TypeError, ValueError):
        return str(value)


def to_error_object(value: Any, fallback_message: str) -> Exception:
    if isinstance(value, Exception):
        return value
    if isinstance(value, str):
        return Exception(value)
    error = Exception(fallback_message)
    if isinstance(value, (dict, list)):
        for key, val in value.items():
            setattr(error, key, val)
    return error


def format_uncaught_error(err: Any) -> str:
    if extract_error_code(err) == "INVALID_CONFIG":
        return format_error_message(err)
    if isinstance(err, Exception):
        return err.stack or err.message or err.name or ""
    return format_error_message(err)


ErrorKind = Optional[str]


def detect_error_kind(err: Any) -> ErrorKind:
    if err is None:
        return None
    message = format_error_message(err).lower()
    code = (extract_error_code(err) or "").lower()
    if "refusal" in message or "content_filter" in message or "sensitive" in message:
        return "refusal"
    if "timeout" in message or code in {"etimedout", "timeout"}:
        return "timeout"
    if "rate limit" in message or "too many requests" in message or "429" in message or code == "429":
        return "rate_limit"
    if "context length" in message or "too many tokens" in message or "token limit" in message:
        return "context_length"
    return None
