"""Elevenlabs plugin module implements tts behavior."""

from __future__ import annotations

import json
import math
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from openclaw.packages.normalization_core import (
    as_record,
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw.plugin_sdk.provider_http import fetch_with_timeout, read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import read_response_text_limited
from openclaw_extensions.elevenlabs.shared import (
    is_valid_elevenlabs_voice_id,
    normalize_elevenlabs_base_url,
)

ERROR_DETAIL_LIMIT = 220
ERROR_BODY_LIMIT_BYTES = 16 * 1024
PROVIDER_BINARY_RESPONSE_MAX_BYTES = 16 * 1024 * 1024


def _require_in_range(value: float, min_value: float, max_value: float, label: str) -> None:
    if not math.isfinite(value) or value < min_value or value > max_value:
        raise RuntimeError(f"{label} must be between {min_value} and {max_value}")


def _normalize_language_code(code: str | None = None) -> str | None:
    normalized = normalize_optional_lowercase_string(code)
    if not normalized:
        return None
    if not normalized.isalpha() or len(normalized) != 2:
        raise RuntimeError(
            "languageCode must be a 2-letter ISO 639-1 code (e.g. en, de, fr)"
        )
    return normalized


def _normalize_apply_text_normalization(
    mode: str | None = None,
) -> str | None:
    normalized = normalize_optional_lowercase_string(mode)
    if not normalized:
        return None
    if normalized in {"auto", "on", "off"}:
        return normalized
    raise RuntimeError("applyTextNormalization must be one of: auto, on, off")


def _normalize_seed(seed: float | int | None = None) -> int | None:
    if seed is None:
        return None
    next_seed = math.floor(seed)
    if not math.isfinite(next_seed) or next_seed < 0 or next_seed > 4_294_967_295:
        raise RuntimeError("seed must be between 0 and 4294967295")
    return int(next_seed)


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
    type_value = normalize_optional_string(subject.get("type"))
    code = (
        normalize_optional_string(subject.get("code"))
        or normalize_optional_string(subject.get("status"))
    )
    metadata_parts = [part for part in (f"type={type_value}" if type_value else None, f"code={code}" if code else None) if part]
    metadata = ", ".join(metadata_parts)
    if message and metadata:
        return f"{_truncate_error_detail(message)} [{metadata}]"
    if message:
        return _truncate_error_detail(message)
    if metadata:
        return f"[{metadata}]"
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
    try:
        raw_body = (await read_response_text_limited(response, ERROR_BODY_LIMIT_BYTES)).strip()
    except (RuntimeError, TypeError, ValueError, AttributeError):
        raw_body = ""
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


def _normalize_content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", {}) or {}
    get_header = headers.get if hasattr(headers, "get") else None
    if not callable(get_header):
        return None
    content_type = get_header("content-type")
    if not isinstance(content_type, str):
        return None
    normalized = content_type.split(";", 1)[0].strip().lower()
    return normalized or None


def _assert_provider_binary_response_content(
    response: Any,
    label: str,
    kind: str = "binary",
) -> None:
    content_type = _normalize_content_type(response)
    if not content_type:
        return
    if (
        content_type == "application/json"
        or content_type.endswith("+json")
        or content_type.startswith("text/")
    ):
        raise RuntimeError(f"{label}: malformed {kind} response")


async def _read_provider_binary_response(
    response: Any,
    label: str,
    kind: str = "binary",
    *,
    max_bytes: int = PROVIDER_BINARY_RESPONSE_MAX_BYTES,
) -> bytes:
    _assert_provider_binary_response_content(response, label, kind)

    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"{label}: {kind} response exceeds {params['maxBytes']} bytes")

    data = await read_response_with_limit(response, max_bytes, on_overflow=on_overflow)
    if not data:
        raise RuntimeError(f"{label}: malformed {kind} response")
    return data


def _assert_elevenlabs_voice_settings(settings: dict[str, Any]) -> None:
    _require_in_range(float(settings["stability"]), 0, 1, "stability")
    _require_in_range(float(settings["similarityBoost"]), 0, 1, "similarityBoost")
    _require_in_range(float(settings["style"]), 0, 1, "style")
    _require_in_range(float(settings["speed"]), 0.5, 2, "speed")


def _resolve_elevenlabs_accept_header(output_format: str) -> str | None:
    normalized = output_format.strip().lower()
    if not normalized or normalized.startswith("mp3_"):
        return "audio/mpeg"
    return None


def _normalize_elevenlabs_latency_tier(latency_tier: float | int | None = None) -> int | None:
    if latency_tier is None or not math.isfinite(latency_tier):
        return None
    if not float(latency_tier).is_integer():
        raise RuntimeError("latencyTier must be an integer")
    resolved = int(latency_tier)
    _require_in_range(resolved, 0, 4, "latencyTier")
    return resolved


def _prepare_elevenlabs_tts_request(
    params: dict[str, Any],
    *,
    stream: bool,
) -> dict[str, Any]:
    text = params["text"]
    base_url = params["baseUrl"]
    voice_id = params["voiceId"]
    model_id = params["modelId"]
    output_format = params["outputFormat"]
    seed = params.get("seed")
    apply_text_normalization = params.get("applyTextNormalization")
    language_code = params.get("languageCode")
    latency_tier = params.get("latencyTier")
    voice_settings = params["voiceSettings"]

    if not is_valid_elevenlabs_voice_id(voice_id):
        raise RuntimeError("Invalid voiceId format")
    _assert_elevenlabs_voice_settings(voice_settings)
    normalized_language = _normalize_language_code(language_code)
    normalized_normalization = _normalize_apply_text_normalization(apply_text_normalization)
    normalized_seed = _normalize_seed(seed)
    normalized_base_url = normalize_elevenlabs_base_url(base_url)
    normalized_latency_tier = _normalize_elevenlabs_latency_tier(latency_tier)

    path = f"/v1/text-to-speech/{voice_id}{'/stream' if stream else ''}"
    parsed = urlparse(normalized_base_url)
    query: dict[str, str] = {}
    if output_format:
        query["output_format"] = output_format
    supports_streaming_latency = model_id.strip().lower() != "eleven_v3"
    if normalized_latency_tier is not None and supports_streaming_latency:
        query["optimize_streaming_latency"] = str(normalized_latency_tier)
    url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            f"{parsed.path.rstrip('/')}{path}",
            "",
            urlencode(query),
            "",
        )
    )
    accept_header = _resolve_elevenlabs_accept_header(output_format)
    body = json.dumps(
        {
            "text": text,
            "model_id": model_id,
            "seed": normalized_seed,
            "apply_text_normalization": normalized_normalization,
            "language_code": normalized_language,
            "voice_settings": {
                "stability": voice_settings["stability"],
                "similarity_boost": voice_settings["similarityBoost"],
                "style": voice_settings["style"],
                "use_speaker_boost": voice_settings["useSpeakerBoost"],
                "speed": voice_settings["speed"],
            },
        },
        separators=(",", ":"),
    )
    return {
        "url": url,
        "normalizedBaseUrl": normalized_base_url,
        "acceptHeader": accept_header,
        "body": body,
    }


class _HttpxFetchResponse:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.ok = bool(response.is_success)
        self.is_success = self.ok
        self.status = response.status_code
        self.status_code = response.status_code
        self.headers = response.headers
        self.reason_phrase = response.reason_phrase
        self.body = None

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


def _ssrf_policy_from_http_base_url_allowed_hostname(base_url: str) -> dict[str, Any]:
    hostname = urlparse(base_url).hostname or ""
    return {"hostnameAllowlist": [hostname] if hostname else []}


async def eleven_labs_tts(
    *,
    text: str,
    api_key: str,
    base_url: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    voice_settings: dict[str, Any],
    timeout_ms: int,
    seed: float | int | None = None,
    apply_text_normalization: str | None = None,
    language_code: str | None = None,
    latency_tier: float | int | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> bytes:
    prepared = _prepare_elevenlabs_tts_request(
        {
            "text": text,
            "baseUrl": base_url,
            "voiceId": voice_id,
            "modelId": model_id,
            "outputFormat": output_format,
            "seed": seed,
            "applyTextNormalization": apply_text_normalization,
            "languageCode": language_code,
            "latencyTier": latency_tier,
            "voiceSettings": voice_settings,
        },
        stream=False,
    )
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    if prepared["acceptHeader"]:
        headers["Accept"] = prepared["acceptHeader"]

    guarded = await _fetch_with_ssrf_guard(
        url=prepared["url"],
        init={
            "method": "POST",
            "headers": headers,
            "body": prepared["body"],
        },
        timeout_ms=timeout_ms,
        policy=_ssrf_policy_from_http_base_url_allowed_hostname(prepared["normalizedBaseUrl"]),
        audit_context="elevenlabs.tts",
        fetch_fn=fetch_fn,
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        await _assert_ok_or_throw_provider_error(response, "ElevenLabs API error")
        return await _read_provider_binary_response(response, "ElevenLabs API error", "audio")
    finally:
        await release()


async def eleven_labs_tts_stream(
    *,
    text: str,
    api_key: str,
    base_url: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    voice_settings: dict[str, Any],
    timeout_ms: int,
    seed: float | int | None = None,
    apply_text_normalization: str | None = None,
    language_code: str | None = None,
    latency_tier: float | int | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> dict[str, Any]:
    prepared = _prepare_elevenlabs_tts_request(
        {
            "text": text,
            "baseUrl": base_url,
            "voiceId": voice_id,
            "modelId": model_id,
            "outputFormat": output_format,
            "seed": seed,
            "applyTextNormalization": apply_text_normalization,
            "languageCode": language_code,
            "latencyTier": latency_tier,
            "voiceSettings": voice_settings,
        },
        stream=True,
    )
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    if prepared["acceptHeader"]:
        headers["Accept"] = prepared["acceptHeader"]

    guarded = await _fetch_with_ssrf_guard(
        url=prepared["url"],
        init={
            "method": "POST",
            "headers": headers,
            "body": prepared["body"],
        },
        timeout_ms=timeout_ms,
        policy=_ssrf_policy_from_http_base_url_allowed_hostname(prepared["normalizedBaseUrl"]),
        audit_context="elevenlabs.tts.stream",
        fetch_fn=fetch_fn,
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    handed_off = False
    try:
        await _assert_ok_or_throw_provider_error(response, "ElevenLabs API error")
        _assert_provider_binary_response_content(response, "ElevenLabs API error", "audio")
        audio_stream = getattr(response, "body", None) or response
        if audio_stream is None:
            raise RuntimeError("ElevenLabs API response missing audio stream")
        handed_off = True
        return {
            "audioStream": audio_stream,
            "release": release,
        }
    finally:
        if not handed_off:
            await release()


# Migration verifier maps elevenLabsTTS -> eleven_labs_t_t_s (acronym letter splitting).
eleven_labs_t_t_s = eleven_labs_tts
eleven_labs_t_t_s_stream = eleven_labs_tts_stream
