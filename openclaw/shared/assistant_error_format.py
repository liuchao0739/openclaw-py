"""Assistant error formatting helpers normalize assistant-visible error payloads."""

from __future__ import annotations

import json
import re
from typing import Any


_MALFORMED_STREAMING_FRAGMENT_ERROR_MESSAGE = "OpenClaw transport error: malformed_streaming_fragment"
_MALFORMED_STREAMING_FRAGMENT_USER_MESSAGE = "LLM streaming response contained a malformed fragment. Please try again."
_GENERIC_PROVIDER_INTERNAL_ERROR_USER_MESSAGE = "The AI service returned an internal error. Please try again in a moment."

_ERROR_PAYLOAD_PREFIX_RE = re.compile(
    r"^(?:error|(?:[a-z][\w-]*\s+)?api\s*error|apierror|openai\s*error|anthropic\s*error|gateway\s*error|codex\s*error)(?:\s+\d{3})?[:\s-]+",
    re.IGNORECASE,
)
_HTTP_STATUS_CODE_PREFIX_RE = re.compile(r"^(?:http\s*)?(\d{3})(?:\s*:\s*|\s+)(.+)$", re.IGNORECASE)
_HTML_ERROR_PREFIX_RE = re.compile(r"^\s*(?:<!doctype\s+html\b|<html\b)", re.IGNORECASE)
_HTML_CLOSE_RE = re.compile(r"<\/html>", re.IGNORECASE)
_CLOUDFLARE_HTML_ERROR_CODES = {521, 522, 523, 524, 525, 526, 530}
_STANDALONE_HTML_ERROR_HINT_RE = re.compile(
    r"cloudflare|cdn-cgi/challenge-platform|challenge-error-text|enable javascript and cookies to continue|access denied|forbidden|service unavailable|bad gateway|web server is down|captcha|attention required",
    re.IGNORECASE,
)
_GENERIC_PROVIDER_INTERNAL_ERROR_RE = re.compile(r"an error occurred while processing your request", re.IGNORECASE)
_SUPPORT_REQUEST_ID_RE = re.compile(r"(?:request[\s_-]*id)\s*[:#]?\s*([a-z0-9][a-z0-9_-]{6,}[a-z0-9])", re.IGNORECASE)


def _is_error_payload_object(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("type") == "error":
        return True
    if isinstance(payload.get("request_id"), str) or isinstance(payload.get("requestId"), str):
        return True
    if "error" in payload:
        err = payload.get("error")
        if isinstance(err, dict):
            if (
                isinstance(err.get("message"), str)
                or isinstance(err.get("type"), str)
                or isinstance(err.get("code"), str)
            ):
                return True
        if isinstance(err, str) and isinstance(payload.get("message"), str):
            return True
    return False


def parse_api_error_payload(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    candidates = [trimmed]
    if _ERROR_PAYLOAD_PREFIX_RE.match(trimmed):
        candidates.append(_ERROR_PAYLOAD_PREFIX_RE.sub("", trimmed).strip())
    for candidate in candidates:
        if not candidate.startswith("{") or not candidate.endswith("}"):
            continue
        try:
            parsed = json.loads(candidate)
            if _is_error_payload_object(parsed):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _extract_leading_http_status(raw: str) -> tuple[int, str] | None:
    match = _HTTP_STATUS_CODE_PREFIX_RE.match(raw)
    if not match:
        return None
    try:
        code = int(match.group(1))
    except ValueError:
        return None
    if not (0 <= code <= 599):
        return None
    rest = (match.group(2) or "").strip()
    return (code, rest)


def is_cloudflare_or_html_error_page(raw: str) -> bool:
    trimmed = raw.strip()
    if not trimmed:
        return False
    if (
        _HTML_ERROR_PREFIX_RE.match(trimmed)
        and _HTML_CLOSE_RE.search(trimmed)
        and _STANDALONE_HTML_ERROR_HINT_RE.search(trimmed)
    ):
        return True
    status = _extract_leading_http_status(trimmed)
    if not status or status[0] < 500:
        return False
    if status[0] in _CLOUDFLARE_HTML_ERROR_CODES:
        return True
    return 500 <= status[0] < 600 and _HTML_ERROR_PREFIX_RE.match(status[1]) is not None


def is_generic_provider_internal_error(raw: str) -> bool:
    trimmed = raw.strip()
    if not trimmed:
        return False
    return bool(
        _GENERIC_PROVIDER_INTERNAL_ERROR_RE.search(trimmed)
        and (_SUPPORT_REQUEST_ID_RE.search(trimmed))
    )


def parse_api_error_info(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    http_code = None
    candidate = trimmed
    http_match = re.match(r"^(\d{3})\s+(.+)$", trimmed, re.DOTALL)
    if http_match:
        http_code = http_match.group(1)
        candidate = http_match.group(2).strip()
    payload = parse_api_error_payload(candidate)
    if not payload:
        return None
    request_id = payload.get("request_id") if isinstance(payload.get("request_id"), str) else None
    if request_id is None:
        request_id = payload.get("requestId") if isinstance(payload.get("requestId"), str) else None
    top_type = payload.get("type") if isinstance(payload.get("type"), str) else None
    top_message = payload.get("message") if isinstance(payload.get("message"), str) else None
    err_type = None
    err_message = None
    if isinstance(payload.get("error"), dict):
        err = payload["error"]
        if isinstance(err.get("type"), str):
            err_type = err["type"]
        if err_type is None and isinstance(err.get("code"), str):
            err_type = err["code"]
        if isinstance(err.get("message"), str):
            err_message = err["message"]
    elif isinstance(payload.get("error"), str):
        err_type = payload["error"]
    return {
        "httpCode": http_code,
        "type": err_type or top_type,
        "message": err_message or top_message,
        "requestId": request_id,
    }


def format_raw_assistant_error_for_ui(raw: str | None) -> str:
    trimmed = (raw or "").strip()
    if not trimmed:
        return "LLM request failed with an unknown error."
    if trimmed == _MALFORMED_STREAMING_FRAGMENT_ERROR_MESSAGE:
        return _MALFORMED_STREAMING_FRAGMENT_USER_MESSAGE
    if is_generic_provider_internal_error(trimmed):
        return _GENERIC_PROVIDER_INTERNAL_ERROR_USER_MESSAGE
    leading_status = _extract_leading_http_status(trimmed)
    is_html_challenge = is_cloudflare_or_html_error_page(trimmed)
    if leading_status and is_html_challenge:
        return f"The AI service is temporarily unavailable (HTTP {leading_status[0]}). Please try again in a moment."
    if is_html_challenge:
        return "The provider returned an HTML error page instead of an API response. This usually means a CDN or gateway (e.g. Cloudflare) blocked the request. Retry in a moment or check provider status."
    http_match = _HTTP_STATUS_CODE_PREFIX_RE.match(trimmed)
    if http_match:
        rest = http_match.group(2).strip()
        if not rest.startswith("{"):
            return f"HTTP {http_match.group(1)}: {rest}"
    info = parse_api_error_info(trimmed)
    if info and info.get("message"):
        prefix = f"HTTP {info['httpCode']}" if info.get("httpCode") else "LLM error"
        type_str = f" {info['type']}" if info.get("type") else ""
        return f"{prefix}{type_str}: {info['message']}"
    return trimmed if len(trimmed) <= 600 else f"{trimmed[:600]}..."
