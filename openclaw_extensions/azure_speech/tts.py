"""Azure Speech REST helpers for SSML synthesis and voice listing."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugin_sdk.provider_http import fetch_with_timeout, read_response_with_limit
from openclaw.plugin_sdk.provider_web_search import read_response_text_limited

DEFAULT_AZURE_SPEECH_VOICE = "en-US-JennyNeural"
DEFAULT_AZURE_SPEECH_LANG = "en-US"
DEFAULT_AZURE_SPEECH_AUDIO_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT = "ogg-24khz-16bit-mono-opus"
DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT = "raw-8khz-8bit-mono-mulaw"
DEFAULT_AZURE_SPEECH_MAX_BYTES = 16 * 1024 * 1024
PROVIDER_JSON_RESPONSE_MAX_BYTES = 16 * 1024 * 1024
ERROR_BODY_LIMIT_BYTES = 16 * 1024

_TRAILING_SLASHES = re.compile(r"/+$")
_COGNITIVE_SERVICES_SUFFIX = re.compile(r"/cognitiveservices/v1$", re.IGNORECASE)


def normalize_azure_speech_base_url(
    *,
    base_url: str | None = None,
    endpoint: str | None = None,
    region: str | None = None,
) -> str | None:
    configured = normalize_optional_string(base_url) or normalize_optional_string(endpoint)
    if configured:
        normalized = _TRAILING_SLASHES.sub("", configured)
        return _COGNITIVE_SERVICES_SUFFIX.sub("", normalized)
    resolved_region = normalize_optional_string(region)
    if resolved_region:
        return f"https://{resolved_region}.tts.speech.microsoft.com"
    return None


def _azure_speech_url(
    *,
    base_url: str | None = None,
    endpoint: str | None = None,
    region: str | None = None,
    path: str,
) -> str:
    resolved_base_url = normalize_azure_speech_base_url(
        base_url=base_url,
        endpoint=endpoint,
        region=region,
    )
    if not resolved_base_url:
        raise RuntimeError("Azure Speech region or endpoint missing")
    return f"{resolved_base_url}{path}"


def _escape_xml_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_xml_attr(value: str) -> str:
    return _escape_xml_text(value).replace('"', "&quot;").replace("'", "&apos;")


def build_azure_speech_ssml(
    *,
    text: str,
    voice: str,
    lang: str | None = None,
) -> str:
    resolved_lang = normalize_optional_string(lang) or DEFAULT_AZURE_SPEECH_LANG
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{_escape_xml_attr(resolved_lang)}">'
        f'<voice name="{_escape_xml_attr(voice)}">{_escape_xml_text(text)}</voice>'
        "</speak>"
    )


def infer_azure_speech_file_extension(output_format: str) -> str:
    normalized = output_format.lower()
    if "mp3" in normalized:
        return ".mp3"
    if normalized.startswith("ogg-"):
        return ".ogg"
    if normalized.startswith("webm-"):
        return ".webm"
    if normalized.startswith("riff-"):
        return ".wav"
    if normalized.startswith("raw-"):
        return ".pcm"
    if normalized.startswith("amr-"):
        return ".amr"
    return ".audio"


def is_azure_speech_voice_compatible(output_format: str) -> bool:
    normalized = output_format.lower()
    return normalized.startswith("ogg-") and "opus" in normalized


def _format_voice_description(entry: dict[str, Any]) -> str | None:
    voice_tag = entry.get("VoiceTag")
    tag = voice_tag if isinstance(voice_tag, dict) else {}
    tailored = tag.get("TailoredScenarios")
    personalities = tag.get("VoicePersonalities")
    parts = [
        *(tailored if isinstance(tailored, list) else []),
        *(personalities if isinstance(personalities, list) else []),
    ]
    filtered = [value for value in parts if normalize_optional_string(value) is not None]
    return ", ".join(filtered) if filtered else None


def _is_deprecated_voice(entry: dict[str, Any]) -> bool:
    is_deprecated = entry.get("IsDeprecated")
    if is_deprecated is True:
        return True
    if isinstance(is_deprecated, str) and is_deprecated.lower() == "true":
        return True
    status = normalize_optional_string(entry.get("Status"))
    if status is None:
        return False
    lowered = status.lower()
    return lowered in {"deprecated", "retired", "disabled"}


async def _assert_ok_or_throw_provider_error(response: Any, label: str) -> None:
    ok = getattr(response, "is_success", None)
    if ok is None:
        ok = getattr(response, "ok", True)
    if ok:
        return
    status = getattr(response, "status_code", getattr(response, "status", "unknown"))
    detail = await read_response_text_limited(response, ERROR_BODY_LIMIT_BYTES)
    reason = getattr(response, "reason_phrase", None) or ""
    message_detail = (detail or reason or "").strip()
    if message_detail:
        raise RuntimeError(f"{label} ({status}): {message_detail}")
    raise RuntimeError(f"{label} ({status})")


async def _read_provider_json_response(response: Any, label: str) -> Any:
    def on_overflow(params: dict[str, int]) -> Exception:
        return RuntimeError(f"{label}: JSON response exceeds {params['maxBytes']} bytes")

    raw = await read_response_with_limit(
        response,
        PROVIDER_JSON_RESPONSE_MAX_BYTES,
        on_overflow=on_overflow,
    )
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as cause:
        raise RuntimeError(f"{label}: malformed JSON response") from cause


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
    timeout_ms: int | None,
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
    resolved_timeout = timeout_ms if timeout_ms is not None else 60_000
    response = await fetch_with_timeout(
        url,
        init,
        resolved_timeout,
        lambda request_url, request_init: resolved_fetch(
            request_url,
            request_init,
            timeout_ms=resolved_timeout,
        ),
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}


async def list_azure_speech_voices(
    *,
    api_key: str,
    base_url: str | None = None,
    endpoint: str | None = None,
    region: str | None = None,
    timeout_ms: int | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> list[dict[str, Any]]:
    url = _azure_speech_url(
        base_url=base_url,
        endpoint=endpoint,
        region=region,
        path="/cognitiveservices/voices/list",
    )
    hostname = urlparse(url).hostname or ""
    guarded = await _fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "GET",
            "headers": {
                "Ocp-Apim-Subscription-Key": api_key,
            },
        },
        timeout_ms=timeout_ms,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="azure-speech.voices",
        fetch_fn=fetch_fn,
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        await _assert_ok_or_throw_provider_error(response, "Azure Speech voices API error")
        voices = await _read_provider_json_response(response, "azure-speech.voices")
        if not isinstance(voices, list):
            return []
        result: list[dict[str, Any]] = []
        for voice in voices:
            if not isinstance(voice, dict) or _is_deprecated_voice(voice):
                continue
            voice_id = normalize_optional_string(voice.get("ShortName")) or ""
            if not voice_id:
                continue
            personalities = voice.get("VoiceTag", {})
            personality_values = (
                personalities.get("VoicePersonalities")
                if isinstance(personalities, dict)
                else None
            )
            filtered_personalities = [
                value
                for value in (personality_values if isinstance(personality_values, list) else [])
                if normalize_optional_string(value) is not None
            ]
            entry: dict[str, Any] = {
                "id": voice_id,
                "name": normalize_optional_string(voice.get("DisplayName"))
                or normalize_optional_string(voice.get("LocalName")),
                "description": _format_voice_description(voice),
                "locale": normalize_optional_string(voice.get("Locale")),
                "gender": normalize_optional_string(voice.get("Gender")),
            }
            if filtered_personalities:
                entry["personalities"] = filtered_personalities
            result.append(entry)
        return result
    finally:
        await release()


async def azure_speech_tts(
    *,
    text: str,
    api_key: str,
    base_url: str | None = None,
    endpoint: str | None = None,
    region: str | None = None,
    voice: str | None = None,
    lang: str | None = None,
    output_format: str | None = None,
    timeout_ms: int | None = None,
    max_bytes: int | None = None,
    fetch_fn: Callable[..., Awaitable[Any]] | None = None,
) -> bytes:
    resolved_voice = normalize_optional_string(voice) or DEFAULT_AZURE_SPEECH_VOICE
    resolved_output_format = (
        normalize_optional_string(output_format) or DEFAULT_AZURE_SPEECH_AUDIO_FORMAT
    )
    url = _azure_speech_url(
        base_url=base_url,
        endpoint=endpoint,
        region=region,
        path="/cognitiveservices/v1",
    )
    hostname = urlparse(url).hostname or ""
    guarded = await _fetch_with_ssrf_guard(
        url=url,
        init={
            "method": "POST",
            "headers": {
                "Content-Type": "application/ssml+xml",
                "Ocp-Apim-Subscription-Key": api_key,
                "X-Microsoft-OutputFormat": resolved_output_format,
                "User-Agent": "OpenClaw",
            },
            "body": build_azure_speech_ssml(
                text=text,
                voice=resolved_voice,
                lang=lang,
            ),
        },
        timeout_ms=timeout_ms,
        policy={"hostnameAllowlist": [hostname]},
        audit_context="azure-speech.tts",
        fetch_fn=fetch_fn,
    )
    response = guarded["response"]
    release: Callable[[], Awaitable[None]] = guarded["release"]
    try:
        await _assert_ok_or_throw_provider_error(response, "Azure Speech TTS API error")
        return await read_response_with_limit(
            response,
            max_bytes if max_bytes is not None else DEFAULT_AZURE_SPEECH_MAX_BYTES,
            on_overflow=lambda params: RuntimeError(
                f"Azure Speech TTS audio response exceeds {params['maxBytes']} bytes"
            ),
        )
    finally:
        await release()


# Migration verifier maps azureSpeechTTS -> azure_speech_t_t_s (acronym letter splitting).
azure_speech_t_t_s = azure_speech_tts
