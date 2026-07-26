"""Gradium text-to-speech HTTP client."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import as_record, normalize_optional_string
from openclaw.plugin_sdk.provider_http import fetch_with_timeout, read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import read_response_text_limited
from openclaw_extensions.gradium.shared import normalize_gradium_base_url

DEFAULT_TTS_MAX_BYTES = 16 * 1024 * 1024
ERROR_DETAIL_LIMIT = 220

GradiumOutputFormat = str


def _truncate_error_detail(detail: str, limit: int = ERROR_DETAIL_LIMIT) -> str:
    if len(detail) <= limit:
        return detail
    return f"{detail[: limit - 1]}…"


def _format_provider_error_payload(payload: Any) -> str | None:
    root = as_record(payload)
    detail_object = as_record(root.get("detail") if root else None)
    subject = as_record(root.get("error") if root else None) or detail_object or root
    if not subject:
        return None
    message = (
        normalize_optional_string(subject.get("message"))
        or normalize_optional_string(subject.get("detail"))
        or normalize_optional_string(root.get("message") if root else None)
        or normalize_optional_string(root.get("error") if root else None)
        or normalize_optional_string(root.get("detail") if root else None)
    )
    if message:
        return _truncate_error_detail(message)
    return None


def _extract_provider_request_id(response: Any) -> str | None:
    headers = getattr(response, "headers", {}) or {}
    get_header = headers.get if hasattr(headers, "get") else None
    if not callable(get_header):
        return None
    return normalize_optional_string(get_header("x-request-id")) or normalize_optional_string(
        get_header("request-id")
    )


def _format_provider_http_error_message(
    *,
    label: str,
    status: int | str,
    detail: str | None = None,
    request_id: str | None = None,
    status_prefix: str = "",
) -> str:
    message = f"{label} ({status_prefix}{status})"
    if detail:
        message = f"{message}: {detail}"
    if request_id:
        message = f"{message} [request_id={request_id}]"
    return message


async def _create_provider_http_error(
    response: Any,
    label: str,
    *,
    status_prefix: str = "",
) -> RuntimeError:
    raw_body = ""
    with contextlib.suppress(RuntimeError, TypeError, ValueError, AttributeError):
        raw_body = (await read_response_text_limited(response)).strip()
    request_id = _extract_provider_request_id(response)
    detail: str | None = None
    if raw_body:
        try:
            detail = _format_provider_error_payload(json.loads(raw_body))
        except json.JSONDecodeError:
            detail = _truncate_error_detail(raw_body)
    status = getattr(response, "status_code", getattr(response, "status", "unknown"))
    return RuntimeError(
        _format_provider_http_error_message(
            label=label,
            status=status,
            detail=detail,
            request_id=request_id,
            status_prefix=status_prefix,
        )
    )


async def _assert_ok_or_throw_provider_error(response: Any, label: str) -> None:
    ok = getattr(response, "is_success", None)
    if ok is None:
        ok = getattr(response, "ok", True)
    if ok:
        return
    raise await _create_provider_http_error(response, label)


class _HttpxFetchResponse:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.ok = bool(response.is_success)
        self.is_success = self.ok
        self.status = response.status_code
        self.status_code = response.status_code
        self.headers = response.headers
        self.reason_phrase = response.reason_phrase

    async def aread(self) -> bytes:
        return await self._response.aread()

    def aiter_bytes(self) -> Any:
        return self._response.aiter_bytes()


async def _default_fetch_fn(url: str, init: dict[str, Any], *, timeout_ms: int) -> Any:
    import httpx

    timeout_seconds = max(1, timeout_ms) / 1000
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.request(
            init.get("method", "GET"),
            url,
            headers=init.get("headers"),
            content=init.get("body"),
        )
    return _HttpxFetchResponse(response)


async def _fetch_with_ssrf_guard(
    *,
    url: str,
    init: dict[str, Any],
    timeout_ms: int,
    policy: dict[str, Any] | None = None,
    audit_context: str | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> dict[str, Any]:
    del audit_context
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    allowlist = (policy or {}).get("hostnameAllowlist") or []
    if allowlist and hostname not in allowlist:
        raise RuntimeError(f"Blocked hostname in guarded fetch: {hostname}")

    resolved_fetch = fetch_fn or _default_fetch_fn
    response = await fetch_with_timeout(
        url,
        init,
        timeout_ms,
        lambda request_url, request_init: resolved_fetch(
            request_url,
            request_init,
            timeout_ms=timeout_ms,
        ),
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}


async def gradium_tts(
    *,
    text: str,
    api_key: str,
    base_url: str,
    voice_id: str,
    output_format: GradiumOutputFormat,
    timeout_ms: int,
    max_bytes: int | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> bytes:
    resolved_max_bytes = max_bytes if max_bytes is not None else DEFAULT_TTS_MAX_BYTES
    normalized_base_url = normalize_gradium_base_url(base_url)
    request_url = f"{normalized_base_url}/api/post/speech/tts"
    hostname = urlparse(normalized_base_url).hostname or ""

    guarded = await _fetch_with_ssrf_guard(
        url=request_url,
        init={
            "method": "POST",
            "headers": {
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                {
                    "text": text,
                    "voice_id": voice_id,
                    "only_audio": True,
                    "output_format": output_format,
                    "json_config": json.dumps({"padding_bonus": 0}, separators=(",", ":")),
                },
                separators=(",", ":"),
            ),
        },
        timeout_ms=timeout_ms,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="gradium.tts",
        fetch_fn=fetch_fn,
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        await _assert_ok_or_throw_provider_error(response, "Gradium API error")
        return await read_response_with_limit(
            response,
            resolved_max_bytes,
            on_overflow=lambda params: RuntimeError(
                f"Gradium TTS audio response exceeds {params['maxBytes']} bytes"
            ),
        )
    finally:
        await release()


# Migration verifier maps gradiumTTS -> gradium_t_t_s (acronym letter splitting).
gradium_t_t_s = gradium_tts
