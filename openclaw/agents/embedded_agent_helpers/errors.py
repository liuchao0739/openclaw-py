"""Provider failure classification helpers (errors.ts parity, incremental)."""

from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

from openclaw.agents.embedded_agent_helpers.failover_matches import (
    is_billing_error_message,
    is_rate_limit_error_message,
)
from openclaw.agents.embedded_agent_helpers.provider_error_patterns import (
    matches_provider_context_overflow,
)

GENERIC_ASSISTANT_ERROR_TEXT = "LLM request failed."

CONTEXT_WINDOW_TOO_SMALL_RE = re.compile(
    r"context window.*(too small|minimum is)", re.IGNORECASE
)
CONTEXT_OVERFLOW_HINT_RE = re.compile(
    r"context.*overflow|context window.*(too (?:large|long)|exceed|over|limit|max(?:imum)?|requested|sent|tokens)|"
    r"prompt.*(too (?:large|long)|exceed|over|limit|max(?:imum)?)|"
    r"(?:request|input).*(?:context|window|length|token).*(too (?:large|long)|exceed|over|limit|max(?:imum)?)",
    re.IGNORECASE,
)
RATE_LIMIT_HINT_RE = re.compile(
    r"rate limit|too many requests|requests per (?:minute|hour|day)|quota|throttl|429\b|tokens per day",
    re.IGNORECASE,
)

OBSERVED_OVERFLOW_TOKEN_PATTERNS = [
    re.compile(r"prompt is too long:\s*([\d,]+)\s+tokens\s*>\s*[\d,]+\s+maximum", re.I),
    re.compile(
        r"prompt is too long:\s*([\d,]+)\s*,\s*model maximum context length\s*:\s*[\d,]+", re.I
    ),
    re.compile(r"requested\s+([\d,]+)\s+tokens", re.I),
    re.compile(r"token limit\s*:\s*[\d,]+\s*\(requested\s*:\s*([\d,]+)\)", re.I),
    re.compile(r"resulted in\s+([\d,]+)\s+tokens", re.I),
]
OBSERVED_OVERFLOW_TOKEN_SUM_PATTERNS = [
    re.compile(
        r"input length(?:\s+and\s+max_tokens)?\s+exceed\s+context(?:\s+limit|\s+window)?\s*"
        r"\(i\.e\s*([\d,]+)\s*\+\s*([\d,]+)\s*>\s*[\d,]+\)",
        re.I,
    ),
]

TRANSIENT_HTTP_ERROR_CODES = frozenset(
    {499, 500, 502, 503, 504, 521, 522, 523, 524, 529}
)

FailoverReason = Literal[
    "auth",
    "auth_permanent",
    "format",
    "rate_limit",
    "overloaded",
    "billing",
    "server_error",
    "timeout",
    "model_not_found",
    "session_expired",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
]


class FailoverSignal(TypedDict, total=False):
    status: int
    code: str
    errorType: str
    message: str
    provider: str
    details: list[str]


def _lower(raw: str) -> str:
    return raw.strip().lower()


def is_reasoning_constraint_error_message(raw: str) -> bool:
    if not raw:
        return False
    lower = _lower(raw)
    return (
        "reasoning is mandatory" in lower
        or "reasoning is required" in lower
        or "requires reasoning" in lower
        or ("reasoning" in lower and "cannot be disabled" in lower)
    )


def _has_rate_limit_tpm_hint(raw: str) -> bool:
    lower = _lower(raw)
    return bool(re.search(r"\btpm\b", lower)) or "tokens per minute" in lower


def is_context_overflow_error(error_message: str | None = None) -> bool:
    if not error_message:
        return False
    lower = _lower(error_message)
    if _has_rate_limit_tpm_hint(error_message):
        return False
    if is_reasoning_constraint_error_message(error_message):
        return False
    has_request_size_exceeds = "request size exceeds" in lower
    has_context_window = (
        "context window" in lower
        or "context length" in lower
        or "maximum context length" in lower
    )
    has_context_window_out_of_room = has_context_window and (
        "ran out of room" in lower or "ran out of space" in lower
    )
    return (
        "request_too_large" in lower
        or ("invalid_argument" in lower and "maximum number of tokens" in lower)
        or "request exceeds the maximum size" in lower
        or "context length exceeded" in lower
        or "maximum context length" in lower
        or "prompt is too long" in lower
        or "prompt too long" in lower
        or "exceeds model context window" in lower
        or "model token limit" in lower
        or ("input exceeds" in lower and "maximum number of tokens" in lower)
        or has_context_window_out_of_room
        or (has_request_size_exceeds and has_context_window)
        or "context overflow:" in lower
        or "exceed context limit" in lower
        or "exceeds the model's maximum context" in lower
        or (
            "max_tokens" in lower
            and "exceed" in lower
            and "context" in lower
        )
        or (
            "input length" in lower
            and "exceed" in lower
            and "context" in lower
        )
        or ("413" in lower and "too large" in lower)
        or "context_window_exceeded" in lower
        or "上下文过长" in error_message
        or "上下文超出" in error_message
        or "上下文长度超" in error_message
        or "超出最大上下文" in error_message
        or "请压缩上下文" in error_message
        or matches_provider_context_overflow(error_message)
    )


def is_likely_context_overflow_error(error_message: str | None = None) -> bool:
    if not error_message:
        return False
    if _has_rate_limit_tpm_hint(error_message):
        return False
    if is_reasoning_constraint_error_message(error_message):
        return False
    if is_billing_error_message(error_message):
        return False
    if CONTEXT_WINDOW_TOO_SMALL_RE.search(error_message):
        return False
    if is_rate_limit_error_message(error_message):
        return False
    if is_context_overflow_error(error_message):
        return True
    if RATE_LIMIT_HINT_RE.search(error_message):
        return False
    return bool(CONTEXT_OVERFLOW_HINT_RE.search(error_message))


def is_compaction_failure_error(error_message: str | None = None) -> bool:
    if not error_message:
        return False
    lower = _lower(error_message)
    has_compaction = (
        "summarization failed" in lower
        or "auto-compaction" in lower
        or "compaction failed" in lower
        or "compaction" in lower
    )
    if not has_compaction:
        return False
    if is_likely_context_overflow_error(error_message):
        return True
    return "context overflow" in lower


def extract_observed_overflow_token_count(error_message: str | None = None) -> int | None:
    if not error_message:
        return None
    for pattern in OBSERVED_OVERFLOW_TOKEN_SUM_PATTERNS:
        match = pattern.search(error_message)
        if not match:
            continue
        left = int(match.group(1).replace(",", ""))
        right = int(match.group(2).replace(",", ""))
        if left > 0 and right >= 0:
            return left + right
    for pattern in OBSERVED_OVERFLOW_TOKEN_PATTERNS:
        match = pattern.search(error_message)
        if not match:
            continue
        parsed = int(match.group(1).replace(",", ""))
        if parsed > 0:
            return parsed
    return None


def is_transient_http_error(raw: str) -> bool:
    if not raw:
        return False
    for code in TRANSIENT_HTTP_ERROR_CODES:
        if str(code) in raw:
            return True
    lower = _lower(raw)
    return "bad gateway" in lower or "service unavailable" in lower or "gateway timeout" in lower


def classify_failover_reason_from_http_status(status: int | None) -> FailoverReason | None:
    if status is None:
        return None
    if status == 401 or status == 403:
        return "auth"
    if status == 402:
        return "billing"
    if status == 404:
        return "model_not_found"
    if status == 408 or status == 504:
        return "timeout"
    if status == 429:
        return "rate_limit"
    if status in TRANSIENT_HTTP_ERROR_CODES:
        return "server_error"
    return None


def is_missing_tool_call_input_error(raw: str) -> bool:
    if not raw:
        return False
    lower = _lower(raw)
    return "tool_use" in lower and "tool_result" in lower and (
        "without" in lower or "missing" in lower
    )


def is_cloud_code_assist_format_error(raw: str) -> bool:
    if not raw:
        return False
    lower = _lower(raw)
    return "cloud code assist" in lower or "invalid json schema" in lower


def is_image_size_error(error_message: str | None = None) -> bool:
    if not error_message:
        return False
    lower = _lower(error_message)
    return "image" in lower and ("too large" in lower or "exceeds" in lower or "size" in lower)


def format_assistant_error_text(msg: dict[str, Any] | None, **_kwargs: Any) -> str:
    if not msg:
        return GENERIC_ASSISTANT_ERROR_TEXT
    err = msg.get("errorMessage")
    if isinstance(err, str) and err.strip():
        return err.strip()
    content = msg.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return GENERIC_ASSISTANT_ERROR_TEXT