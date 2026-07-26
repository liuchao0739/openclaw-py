"""Public media-understanding helpers for provider plugins.

Mirrors src/plugin-sdk/media-understanding.ts exports used by bundled providers.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw.plugin_sdk.provider_http import (
    DEFAULT_GUARDED_HTTP_TIMEOUT_MS,
    _FetchResponse,
    assert_ok_or_throw_http_error,
    fetch_with_timeout,
    resolve_provider_http_request_config,
)

OPENAI_AUDIO_TRANSCRIPTIONS_API = "openai-audio-transcriptions"


def resolve_audio_transcription_upload_file_name(
    file_name: str | None,
    mime: str | None = None,
) -> str:
    """Resolve the multipart upload filename, mapping AAC inputs to provider-friendly `.m4a`."""
    trimmed = file_name.strip() if isinstance(file_name, str) else ""
    base_name = os.path.basename(trimmed) if trimmed else "audio"
    lower_mime = mime.strip().lower() if isinstance(mime, str) else None

    if re.search(r"\.aac$", base_name, re.IGNORECASE):
        return f"{base_name[:-4] or 'audio'}.m4a"
    if not os.path.splitext(base_name)[1] and lower_mime == "audio/aac":
        return f"{base_name or 'audio'}.m4a"
    return base_name


def build_audio_transcription_form_data(params: dict[str, Any]) -> dict[str, Any]:
    """Build provider-compatible multipart form fields for audio transcription requests."""
    buffer = params["buffer"]
    upload_name = resolve_audio_transcription_upload_file_name(
        params.get("fileName"),
        params.get("mime"),
    )
    mime = params.get("mime") or "application/octet-stream"
    files = {"file": (upload_name, buffer, mime)}
    data: dict[str, str] = {}
    for name, value in (params.get("fields") or {}).items():
        if value is None:
            continue
        text = value.strip() if isinstance(value, str) else str(value)
        if text:
            data[name] = text
    return {"files": files, "data": data}


def require_transcription_text(value: str | None, missing_message: str) -> str:
    """Return trimmed transcription text or raise when the provider omitted it."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise RuntimeError(missing_message)
    return text


async def read_provider_json_object_response(response: Any, label: str) -> dict[str, Any]:
    """Parse a provider JSON response and require a top-level object payload."""
    try:
        payload = await response.json()
    except (AttributeError, TypeError, json.JSONDecodeError, ValueError):
        raise RuntimeError(f"{label}: malformed JSON response") from None
    if not isinstance(payload, dict):
        raise TypeError(f"{label}: malformed JSON response")
    return payload


async def _default_multipart_fetch_fn(url: str, init: dict[str, Any]) -> _FetchResponse:
    import httpx

    multipart = init.get("multipart")
    if not isinstance(multipart, dict):
        raise TypeError("multipart request requires multipart init payload")
    timeout_seconds = max(1, int(init.get("timeoutMs", DEFAULT_GUARDED_HTTP_TIMEOUT_MS))) / 1000
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            url,
            headers=init.get("headers"),
            files=multipart.get("files"),
            data=multipart.get("data"),
        )
    return _FetchResponse(response)


async def post_transcription_request(params: dict[str, Any]) -> dict[str, Any]:
    """POST a multipart transcription request and return the response plus release hook."""
    fetch_fn = params.get("fetchFn") or _default_multipart_fetch_fn
    timeout_ms = params.get("timeoutMs", DEFAULT_GUARDED_HTTP_TIMEOUT_MS)
    response = await fetch_with_timeout(
        params["url"],
        {
            "method": "POST",
            "headers": params.get("headers") or {},
            "multipart": params.get("multipart"),
            "timeoutMs": timeout_ms,
        },
        timeout_ms,
        fetch_fn,
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}


def _resolve_model(model: str | None, fallback: str) -> str:
    trimmed = model.strip() if isinstance(model, str) else ""
    return trimmed or fallback


async def transcribe_open_ai_compatible_audio(params: dict[str, Any]) -> dict[str, str]:
    """Send an OpenAI-compatible audio transcription request and return validated text output."""
    fetch_fn = params.get("fetchFn") or _default_multipart_fetch_fn
    auth = params.get("auth") if isinstance(params.get("auth"), dict) else None
    api_key = auth.get("apiKey") if auth and auth.get("kind") == "api-key" else params.get("apiKey")
    default_headers = None
    if auth and auth.get("kind") == "none":
        default_headers = None
    elif api_key:
        default_headers = {"authorization": f"Bearer {api_key}"}

    request_config = resolve_provider_http_request_config(
        {
            "baseUrl": params.get("baseUrl"),
            "defaultBaseUrl": params["defaultBaseUrl"],
            "headers": params.get("headers"),
            "request": params.get("request"),
            "defaultHeaders": default_headers,
            "provider": params.get("provider"),
            "api": OPENAI_AUDIO_TRANSCRIPTIONS_API,
            "capability": "audio",
            "transport": "media-understanding",
        }
    )
    url = f"{request_config['baseUrl']}/audio/transcriptions"
    model = _resolve_model(params.get("model"), params["defaultModel"])
    multipart = build_audio_transcription_form_data(
        {
            "buffer": params["buffer"],
            "fileName": params.get("fileName"),
            "mime": params.get("mime"),
            "fields": {
                "model": model,
                "language": params.get("language"),
                "prompt": params.get("prompt"),
            },
        }
    )

    result = await post_transcription_request(
        {
            "url": url,
            "headers": request_config["headers"],
            "multipart": multipart,
            "timeoutMs": params.get("timeoutMs"),
            "fetchFn": fetch_fn,
        }
    )
    response = result["response"]
    release: Callable[[], Awaitable[None]] = result["release"]
    try:
        await assert_ok_or_throw_http_error(response, "Audio transcription failed")
        payload = await read_provider_json_object_response(response, "Audio transcription failed")
        text_value = payload.get("text")
        text = require_transcription_text(
            text_value if isinstance(text_value, str) else None,
            "Audio transcription response missing text",
        )
        return {"text": text, "model": model}
    finally:
        await release()
