"""Convert raw provider/transport errors into concise user-facing copy."""

from __future__ import annotations

import json
import re
from typing import Any

from openclaw.agents.embedded_agent_helpers.failover_matches import (
    is_billing_error_message,
    is_overloaded_error_message,
    is_rate_limit_error_message,
    is_timeout_error_message,
)

MALFORMED_STREAMING_FRAGMENT_ERROR_MESSAGE = (
    "LLM streaming response contained a malformed JSON fragment."
)

BILLING_ERROR_USER_MESSAGE = (
    "⚠️ API provider returned a billing error — your API key has run out of credits "
    "or has an insufficient balance. Check your provider's billing dashboard and top up "
    "or switch to a different API key."
)
RATE_LIMIT_ERROR_USER_MESSAGE = "⚠️ API rate limit reached. Please try again later."
MODEL_CAPACITY_ERROR_USER_MESSAGE = (
    "⚠️ Selected model is at capacity. Try a different model, or wait and retry."
)
OVERLOADED_ERROR_USER_MESSAGE = (
    "The AI service is temporarily overloaded. Please try again in a moment."
)

TOOL_CALLS_OMITTED_PLACEHOLDER_LINE_RE = re.compile(
    r"^[ \t]*\[tool calls omitted\][ \t]*$", re.IGNORECASE
)
ERROR_PREFIX_RE = re.compile(
    r"^(?:error|(?:[a-z][\w-]*\s+)?api\s*error|openai\s*error|anthropic\s*error|"
    r"gateway\s*error|codex\s*error|request failed|failed|exception)(?:\s+\d{3})?[:\s-]+",
    re.IGNORECASE,
)
CONTEXT_OVERFLOW_ERROR_HEAD_RE = re.compile(
    r"^(?:context overflow:|request_too_large\b|request size exceeds\b|"
    r"request exceeds the maximum size\b|context length exceeded\b|maximum context length\b|"
    r"prompt is too long\b|exceeds model context window\b)",
    re.IGNORECASE,
)
HTTP_ERROR_HINTS = (
    "error",
    "bad request",
    "not found",
    "unauthorized",
    "forbidden",
    "internal server",
    "service unavailable",
    "gateway",
    "rate limit",
    "overloaded",
    "timeout",
    "timed out",
    "invalid",
    "too many requests",
    "permission",
)
RATE_LIMIT_SPECIFIC_HINT_RE = re.compile(
    r"\bmin(ute)?s?\b|\bhours?\b|\bseconds?\b|\btry again in\b|\breset\b|\bquota\b",
    re.IGNORECASE,
)
MODEL_CAPACITY_ERROR_RE = re.compile(r"\b(?:selected\s+)?model\s+(?:is\s+)?at capacity\b", re.I)
LEADING_HTTP_STATUS_RE = re.compile(r"^(\d{3})\s+(.+)$", re.DOTALL)
HTML_ERROR_RE = re.compile(r"(?:<!doctype\s+html\b|<html\b)", re.I)


def format_billing_error_message(
    provider: str | None = None,
    model: str | None = None,
    auth_mode: str | None = None,
) -> str:
    provider_name = (provider or "").strip()
    model_name = (model or "").strip()
    provider_label = (
        f"{provider_name} ({model_name})" if provider_name and model_name else provider_name or None
    )
    if auth_mode in ("oauth", "token"):
        if provider_label:
            return (
                f"⚠️ {provider_label} returned a billing error — check your account for "
                "subscription or usage limits, then try again."
            )
        return (
            "⚠️ API provider returned a billing error — check your account for subscription "
            "or usage limits, then try again."
        )
    if provider_label:
        return (
            f"⚠️ {provider_label} returned a billing error — your API key has run out of credits "
            f"or has an insufficient balance. Check your {provider_name} billing dashboard "
            "and top up or switch to a different API key."
        )
    return BILLING_ERROR_USER_MESSAGE


def _coerce_chat_content_text(text: Any) -> str:
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    return str(text)


def _extract_leading_http_status(raw: str) -> tuple[int, str] | None:
    m = LEADING_HTTP_STATUS_RE.match(raw.strip())
    if not m:
        return None
    code = int(m.group(1))
    return code, m.group(2).strip()


def _is_cloudflare_or_html_error_page(raw: str) -> bool:
    return bool(HTML_ERROR_RE.search(raw.strip()))


def _parse_api_error_payload(raw: str) -> dict[str, Any] | None:
    trimmed = raw.strip()
    if not trimmed.startswith("{"):
        return None
    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def get_api_error_payload_fingerprint(raw: str | None = None) -> str | None:
    if not raw:
        return None
    payload = _parse_api_error_payload(raw)
    if not payload:
        return None
    return json.dumps(payload, sort_keys=True)


def is_raw_api_error_payload(raw: str | None = None) -> bool:
    return get_api_error_payload_fingerprint(raw) is not None


def is_invalid_streaming_event_order_error(raw: str) -> bool:
    if not raw:
        return False
    lower = raw.strip().lower()
    return (
        "unexpected event order" in lower
        and "message_start" in lower
        and "message_stop" in lower
    )


def is_streaming_json_parse_error(raw: str) -> bool:
    if not raw:
        return False
    return raw.strip() == MALFORMED_STREAMING_FRAGMENT_ERROR_MESSAGE


def is_likely_http_error_text(raw: str) -> bool:
    if _is_cloudflare_or_html_error_page(raw):
        return True
    status = _extract_leading_http_status(raw)
    if not status:
        return False
    code, rest = status
    if code < 400:
        return False
    message = rest.lower()
    return any(hint in message for hint in HTTP_ERROR_HINTS)


def format_rate_limit_or_overloaded_error_copy(raw: str) -> str | None:
    if is_rate_limit_error_message(raw):
        return RATE_LIMIT_ERROR_USER_MESSAGE
    if MODEL_CAPACITY_ERROR_RE.search(raw):
        return MODEL_CAPACITY_ERROR_USER_MESSAGE
    if is_overloaded_error_message(raw):
        return OVERLOADED_ERROR_USER_MESSAGE
    return None


def format_transport_error_copy(raw: str) -> str | None:
    if not raw or _is_cloudflare_or_html_error_page(raw):
        return None
    lower = raw.strip().lower()
    if re.search(r"\beconnrefused\b", raw, re.I) or "connection refused" in lower:
        return "LLM request failed: connection refused by the provider endpoint."
    if (
        re.search(r"\beconnreset\b|\beconnaborted\b", raw, re.I)
        or "connection reset" in lower
        or "socket hang up" in lower
    ):
        return "LLM request failed: network connection was interrupted."
    if re.search(r"\benotfound\b", raw, re.I) or "no such host" in lower or "dns" in lower:
        return "LLM request failed: DNS lookup for the provider endpoint failed."
    if "network is unreachable" in lower or "fetch failed" in lower:
        return "LLM request failed: network connection error."
    if "网络错误" in raw or "连接错误" in raw:
        return "LLM request failed: provider reported a network error."
    return None


def format_disk_space_error_copy(raw: str) -> str | None:
    if not raw:
        return None
    lower = raw.strip().lower()
    if re.search(r"\benospc\b", raw, re.I) or "no space left on device" in lower or "disk full" in lower:
        return (
            "OpenClaw could not write local session data because the disk is full. "
            "Free some disk space and try again."
        )
    return None


def _format_raw_assistant_error_for_ui(raw: str) -> str:
    trimmed = raw.strip()
    if trimmed.lower().startswith("error:"):
        return f"LLM request failed: {trimmed[6:].strip()}"
    return f"LLM request failed: {trimmed}"


def _should_rewrite_context_overflow_text(raw: str) -> bool:
    lower = raw.lower()
    if re.search(r"\btpm\b", lower) or "tokens per minute" in lower:
        return False
    looks_overflow = (
        "context overflow:" in lower
        or "context length exceeded" in lower
        or "prompt is too long" in lower
        or "context_window_exceeded" in lower
    )
    if not looks_overflow:
        return False
    return (
        is_raw_api_error_payload(raw)
        or is_likely_http_error_text(raw)
        or bool(ERROR_PREFIX_RE.match(raw))
        or bool(CONTEXT_OVERFLOW_ERROR_HEAD_RE.match(raw))
    )


def _strip_tool_calls_omitted_placeholder_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if not TOOL_CALLS_OMITTED_PLACEHOLDER_LINE_RE.match(line.rstrip("\n\r")))


def sanitize_user_facing_text(text: Any, *, error_context: bool = False) -> str:
    raw = _coerce_chat_content_text(text)
    if not raw:
        return raw
    stripped = _strip_tool_calls_omitted_placeholder_lines(raw)
    trimmed = stripped.strip()
    if not trimmed:
        return ""

    if error_context:
        disk = format_disk_space_error_copy(trimmed)
        if disk:
            return disk
        if re.search(r"incorrect role information|roles must alternate", trimmed, re.I):
            return (
                "Message ordering conflict - please try again. "
                "If this persists, use /new to start a fresh session."
            )
        if _should_rewrite_context_overflow_text(trimmed):
            return (
                "Context overflow: prompt too large for the model. "
                "Try /reset (or /new) to start a fresh session, or use a larger-context model."
            )
        if is_billing_error_message(trimmed):
            return BILLING_ERROR_USER_MESSAGE
        if is_invalid_streaming_event_order_error(trimmed):
            return "LLM request failed: provider returned an invalid streaming response. Please try again."
        if is_raw_api_error_payload(trimmed) or is_likely_http_error_text(trimmed):
            return _format_raw_assistant_error_for_ui(trimmed)
        if is_streaming_json_parse_error(trimmed):
            return "LLM streaming response contained a malformed fragment. Please try again."
        if ERROR_PREFIX_RE.match(trimmed):
            rl = format_rate_limit_or_overloaded_error_copy(trimmed)
            if rl:
                return rl
            transport = format_transport_error_copy(trimmed)
            if transport:
                return transport
            if is_timeout_error_message(trimmed):
                return "LLM request timed out."
            return _format_raw_assistant_error_for_ui(trimmed)

    return stripped.strip()