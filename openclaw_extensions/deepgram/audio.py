"""Deepgram plugin module implements audio behavior."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from openclaw.packages.normalization_core import as_optional_record
from openclaw.plugin_sdk.media_understanding import (
    read_provider_json_object_response,
    require_transcription_text,
)
from openclaw.plugin_sdk.provider_http import (
    DEFAULT_GUARDED_HTTP_TIMEOUT_MS,
    assert_ok_or_throw_http_error,
    default_fetch_fn,
    fetch_with_timeout,
    resolve_provider_http_request_config,
)

DEFAULT_DEEPGRAM_AUDIO_BASE_URL = "https://api.deepgram.com/v1"
DEFAULT_DEEPGRAM_AUDIO_MODEL = "nova-3"


def _resolve_model(model: str | None) -> str:
    trimmed = model.strip() if isinstance(model, str) else ""
    return trimmed or DEFAULT_DEEPGRAM_AUDIO_MODEL


def _read_deepgram_transcript(payload: dict[str, Any]) -> str | None:
    results = as_optional_record(payload.get("results"))
    if results is None:
        return None
    channels = results.get("channels")
    if not isinstance(channels, list):
        raise RuntimeError("Audio transcription failed: malformed JSON response")  # noqa: TRY004
    channel = as_optional_record(channels[0] if channels else None)
    if channel is None:
        return None
    alternatives = channel.get("alternatives")
    if not isinstance(alternatives, list):
        raise RuntimeError("Audio transcription failed: malformed JSON response")  # noqa: TRY004
    alternative = as_optional_record(alternatives[0] if alternatives else None)
    if alternative is None:
        return None
    transcript = alternative.get("transcript")
    if transcript is not None and not isinstance(transcript, str):
        raise RuntimeError("Audio transcription failed: malformed JSON response")
    return transcript


def _build_listen_url(
    *,
    base_url: str,
    model: str,
    language: str | None,
    query: dict[str, Any] | None,
) -> str:
    parsed = urlparse(base_url.rstrip("/"))
    path = f"{parsed.path.rstrip('/')}/listen"
    params: dict[str, str] = {"model": model}
    if language:
        params["language"] = language
    for key, value in (query or {}).items():
        if value is not None:
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
            else:
                params[key] = str(value)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            urlencode(params),
            "",
        )
    )


async def _post_binary_transcription_request(params: dict[str, Any]) -> dict[str, Any]:
    fetch_fn = params.get("fetchFn") or default_fetch_fn
    timeout_ms = params.get("timeoutMs", DEFAULT_GUARDED_HTTP_TIMEOUT_MS)
    response = await fetch_with_timeout(
        params["url"],
        {
            "method": "POST",
            "headers": params.get("headers") or {},
            "body": params["body"],
            "timeoutMs": timeout_ms,
        },
        timeout_ms,
        fetch_fn,
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}


async def transcribe_deepgram_audio(params: dict[str, Any]) -> dict[str, str]:
    fetch_fn = params.get("fetchFn") or default_fetch_fn
    model = _resolve_model(params.get("model"))
    request_config = resolve_provider_http_request_config(
        {
            "baseUrl": params.get("baseUrl"),
            "defaultBaseUrl": DEFAULT_DEEPGRAM_AUDIO_BASE_URL,
            "headers": params.get("headers"),
            "request": params.get("request"),
            "defaultHeaders": {
                "authorization": f"Token {params['apiKey']}",
                "content-type": params.get("mime") or "application/octet-stream",
            },
            "provider": "deepgram",
            "capability": "audio",
            "transport": "media-understanding",
        }
    )

    language = params.get("language")
    language_trimmed = language.strip() if isinstance(language, str) and language.strip() else None
    url = _build_listen_url(
        base_url=request_config["baseUrl"],
        model=model,
        language=language_trimmed,
        query=params.get("query") if isinstance(params.get("query"), dict) else None,
    )

    buffer = params["buffer"]
    body = bytes(buffer) if not isinstance(buffer, bytes) else buffer
    result = await _post_binary_transcription_request(
        {
            "url": url,
            "headers": request_config["headers"],
            "body": body,
            "timeoutMs": params.get("timeoutMs"),
            "fetchFn": fetch_fn,
        }
    )
    response = result["response"]
    release = result["release"]
    try:
        await assert_ok_or_throw_http_error(response, "Audio transcription failed")
        payload = await read_provider_json_object_response(response, "Audio transcription failed")
        transcript = require_transcription_text(
            _read_deepgram_transcript(payload),
            "Audio transcription response missing transcript",
        )
        return {"text": transcript, "model": model}
    finally:
        await release()
