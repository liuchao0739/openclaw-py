"""Deepgram provider module implements model/runtime integration."""

from __future__ import annotations

import math
import os
from typing import Any, Literal
from urllib.parse import urlencode, urlparse, urlunparse

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import (
    as_optional_record,
    normalize_optional_string,
    normalize_stringified_optional_string,
)
from openclaw.plugin_sdk.realtime_transcription import (
    create_realtime_transcription_websocket_session,
)
from openclaw_extensions.deepgram.audio import (
    DEFAULT_DEEPGRAM_AUDIO_BASE_URL,
    DEFAULT_DEEPGRAM_AUDIO_MODEL,
)

DeepgramRealtimeTranscriptionEncoding = Literal["linear16", "mulaw", "alaw"]

DEEPGRAM_REALTIME_DEFAULT_SAMPLE_RATE = 8000
DEEPGRAM_REALTIME_DEFAULT_ENCODING: DeepgramRealtimeTranscriptionEncoding = "mulaw"
DEEPGRAM_REALTIME_DEFAULT_ENDPOINTING_MS = 800
DEEPGRAM_REALTIME_CONNECT_TIMEOUT_MS = 10_000
DEEPGRAM_REALTIME_CLOSE_TIMEOUT_MS = 5_000
DEEPGRAM_REALTIME_MAX_RECONNECT_ATTEMPTS = 5
DEEPGRAM_REALTIME_RECONNECT_DELAY_MS = 1000
DEEPGRAM_REALTIME_MAX_QUEUED_BYTES = 2 * 1024 * 1024


def _parse_boolean_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    normalized = normalize_optional_string(value)
    if not normalized:
        return None
    lowered = normalized.lower()
    if lowered in {"true", "1", "yes", "on"}:
        return True
    if lowered in {"false", "0", "no", "off"}:
        return False
    return None


def _parse_finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    normalized = normalize_stringified_optional_string(value)
    if normalized is None:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _read_nested_deepgram_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    raw = as_optional_record(raw_config) or {}
    providers = as_optional_record(raw.get("providers"))
    nested = as_optional_record(providers.get("deepgram") if providers else None)
    direct = as_optional_record(raw.get("deepgram"))
    return as_optional_record(nested or direct or raw) or {}


def _normalize_deepgram_encoding(value: Any) -> DeepgramRealtimeTranscriptionEncoding | None:
    normalized = normalize_optional_string(value)
    lowered = normalized.lower() if normalized else None
    if not lowered:
        return None
    if lowered in {"pcm", "pcm_s16le", "linear16"}:
        return "linear16"
    if lowered in {"ulaw", "g711_ulaw", "g711-mulaw"}:
        return "mulaw"
    if lowered in {"g711_alaw", "g711-alaw"}:
        return "alaw"
    if lowered in {"mulaw", "alaw"}:
        return lowered  # type: ignore[return-value]
    raise RuntimeError(f"Invalid Deepgram realtime transcription encoding: {lowered}")


def _normalize_deepgram_realtime_base_url(value: str | None = None) -> str:
    return (
        normalize_optional_string(value or os.environ.get("DEEPGRAM_BASE_URL"))
        or DEFAULT_DEEPGRAM_AUDIO_BASE_URL
    )


def to_deepgram_realtime_ws_url(config: dict[str, Any]) -> str:
    parsed = urlparse(_normalize_deepgram_realtime_base_url(config.get("baseUrl")))
    scheme = "ws" if parsed.scheme == "http" else "wss"
    path = f"{parsed.path.rstrip('/')}/listen"
    params = {
        "model": config["model"],
        "encoding": config["encoding"],
        "sample_rate": str(config["sampleRate"]),
        "channels": "1",
        "interim_results": str(config["interimResults"]).lower(),
        "endpointing": str(config["endpointingMs"]),
    }
    language = normalize_optional_string(config.get("language"))
    if language:
        params["language"] = language
    return urlunparse(
        (
            scheme,
            parsed.netloc,
            path,
            "",
            urlencode(params),
            "",
        )
    )


def normalize_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = _read_nested_deepgram_config(config)
    return {
        "apiKey": normalize_secret_input_string(raw.get("apiKey")),
        "baseUrl": normalize_optional_string(raw.get("baseUrl")),
        "model": normalize_optional_string(raw.get("model") or raw.get("sttModel")),
        "language": normalize_optional_string(raw.get("language")),
        "sampleRate": _parse_finite_number(raw.get("sampleRate") or raw.get("sample_rate")),
        "encoding": _normalize_deepgram_encoding(raw.get("encoding")),
        "interimResults": _parse_boolean_value(raw.get("interimResults") or raw.get("interim_results")),
        "endpointingMs": _parse_finite_number(
            raw.get("endpointingMs") or raw.get("endpointing") or raw.get("silenceDurationMs")
        ),
    }


def _read_error_detail(value: Any) -> str:
    if isinstance(value, str):
        return value
    record = as_optional_record(value)
    message = normalize_optional_string(record.get("message") if record else None)
    code = normalize_optional_string(record.get("code") if record else None)
    return message or code or "Deepgram realtime transcription error"


def _read_transcript_text(event: dict[str, Any]) -> str | None:
    channel = as_optional_record(event.get("channel"))
    alternatives = channel.get("alternatives") if channel else None
    if not isinstance(alternatives, list) or not alternatives:
        return None
    first = as_optional_record(alternatives[0])
    return normalize_optional_string(first.get("transcript") if first else None)


def _create_deepgram_realtime_transcription_session(config: dict[str, Any]) -> Any:
    last_transcript: str | None = None
    speech_started = False

    def emit_transcript(text: str) -> None:
        nonlocal last_transcript
        if text == last_transcript:
            return
        last_transcript = text
        on_transcript = config.get("onTranscript")
        if callable(on_transcript):
            on_transcript(text)

    def handle_event(event: dict[str, Any]) -> None:
        nonlocal speech_started
        event_type = event.get("type")
        if event_type == "Results":
            text = _read_transcript_text(event)
            if not text:
                return
            if not speech_started:
                speech_started = True
                on_speech_start = config.get("onSpeechStart")
                if callable(on_speech_start):
                    on_speech_start()
            if event.get("is_final") or event.get("speech_final"):
                emit_transcript(text)
                if event.get("speech_final"):
                    speech_started = False
                return
            on_partial = config.get("onPartial")
            if callable(on_partial):
                on_partial(text)
            return
        if event_type == "SpeechStarted":
            speech_started = True
            on_speech_start = config.get("onSpeechStart")
            if callable(on_speech_start):
                on_speech_start()
            return
        if event_type in {"Error", "error"}:
            on_error = config.get("onError")
            if callable(on_error):
                on_error(RuntimeError(_read_error_detail(event.get("error") or event.get("message"))))

    return create_realtime_transcription_websocket_session(
        {
            "providerId": "deepgram",
            "callbacks": config,
            "url": lambda: to_deepgram_realtime_ws_url(config),
            "headers": {"Authorization": f"Token {config['apiKey']}"},
            "readyOnOpen": True,
            "connectTimeoutMs": DEEPGRAM_REALTIME_CONNECT_TIMEOUT_MS,
            "closeTimeoutMs": DEEPGRAM_REALTIME_CLOSE_TIMEOUT_MS,
            "maxReconnectAttempts": DEEPGRAM_REALTIME_MAX_RECONNECT_ATTEMPTS,
            "reconnectDelayMs": DEEPGRAM_REALTIME_RECONNECT_DELAY_MS,
            "maxQueuedBytes": DEEPGRAM_REALTIME_MAX_QUEUED_BYTES,
            "connectTimeoutMessage": "Deepgram realtime transcription connection timeout",
            "connectClosedBeforeReadyMessage": (
                "Deepgram realtime transcription connection closed before ready"
            ),
            "reconnectLimitMessage": "Deepgram realtime transcription reconnect limit reached",
            "sendAudio": lambda audio, transport: transport.send_binary(audio),
            "onClose": lambda transport: transport.send_json({"type": "Finalize"}),
            "onMessage": handle_event,
        }
    )


def build_deepgram_realtime_transcription_provider() -> dict[str, Any]:
    def resolve_config(params: dict[str, Any]) -> dict[str, Any]:
        raw_config = params.get("rawConfig") if isinstance(params.get("rawConfig"), dict) else {}
        return normalize_provider_config(raw_config)

    def is_configured(params: dict[str, Any]) -> bool:
        provider_config = (
            params.get("providerConfig") if isinstance(params.get("providerConfig"), dict) else {}
        )
        return bool(normalize_provider_config(provider_config).get("apiKey") or os.environ.get("DEEPGRAM_API_KEY"))

    def create_session(req: dict[str, Any]) -> Any:
        provider_config = req.get("providerConfig") if isinstance(req.get("providerConfig"), dict) else {}
        config = normalize_provider_config(provider_config)
        api_key = config.get("apiKey") or os.environ.get("DEEPGRAM_API_KEY")
        if not api_key:
            raise RuntimeError("Deepgram API key missing")
        return _create_deepgram_realtime_transcription_session(
            {
                **req,
                "apiKey": api_key,
                "baseUrl": _normalize_deepgram_realtime_base_url(config.get("baseUrl")),
                "model": config.get("model") or DEFAULT_DEEPGRAM_AUDIO_MODEL,
                "sampleRate": config.get("sampleRate") or DEEPGRAM_REALTIME_DEFAULT_SAMPLE_RATE,
                "encoding": config.get("encoding") or DEEPGRAM_REALTIME_DEFAULT_ENCODING,
                "interimResults": (
                    config.get("interimResults")
                    if config.get("interimResults") is not None
                    else True
                ),
                "endpointingMs": config.get("endpointingMs") or DEEPGRAM_REALTIME_DEFAULT_ENDPOINTING_MS,
                "language": config.get("language"),
            }
        )

    return {
        "id": "deepgram",
        "label": "Deepgram Realtime Transcription",
        "aliases": ["deepgram-realtime", "nova-3-streaming"],
        "defaultModel": DEFAULT_DEEPGRAM_AUDIO_MODEL,
        "autoSelectOrder": 35,
        "resolveConfig": resolve_config,
        "isConfigured": is_configured,
        "createSession": create_session,
    }


testing = {
    "normalizeProviderConfig": normalize_provider_config,
    "toDeepgramRealtimeWsUrl": to_deepgram_realtime_ws_url,
}
__testing__ = testing
