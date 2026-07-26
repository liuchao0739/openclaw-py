"""Elevenlabs provider module implements model/runtime integration."""

from __future__ import annotations

import base64
import os
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import (
    as_finite_number,
    as_record,
    normalize_lowercase_string_or_empty,
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw.plugin_sdk.realtime_transcription import (
    create_realtime_transcription_websocket_session,
)
from openclaw_extensions.elevenlabs.config_api import resolve_eleven_labs_api_key_with_profile_fallback
from openclaw_extensions.elevenlabs.shared import normalize_elevenlabs_base_url

ELEVENLABS_REALTIME_DEFAULT_MODEL = "scribe_v2_realtime"
ELEVENLABS_REALTIME_DEFAULT_AUDIO_FORMAT = "ulaw_8000"
ELEVENLABS_REALTIME_DEFAULT_SAMPLE_RATE = 8000
ELEVENLABS_REALTIME_DEFAULT_COMMIT_STRATEGY = "vad"
ELEVENLABS_REALTIME_CONNECT_TIMEOUT_MS = 10_000
ELEVENLABS_REALTIME_CLOSE_TIMEOUT_MS = 5_000
ELEVENLABS_REALTIME_MAX_RECONNECT_ATTEMPTS = 5
ELEVENLABS_REALTIME_RECONNECT_DELAY_MS = 1000
ELEVENLABS_REALTIME_MAX_QUEUED_BYTES = 2 * 1024 * 1024


def _read_nested_elevenlabs_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    raw = as_record(raw_config) or {}
    providers = as_record(raw.get("providers"))
    nested = as_record(providers.get("elevenlabs") if providers else None)
    direct = as_record(raw.get("elevenlabs"))
    return as_record(nested or direct or raw) or {}


def _normalize_commit_strategy(value: Any) -> str | None:
    normalized = normalize_optional_lowercase_string(value)
    if not normalized:
        return None
    if normalized in {"manual", "vad"}:
        return normalized
    raise RuntimeError(f"Invalid ElevenLabs realtime transcription commit strategy: {normalized}")


def _normalize_positive_safe_integer(value: Any) -> int | None:
    parsed = as_finite_number(value)
    if parsed is None or not float(parsed).is_integer() or parsed <= 0:
        return None
    return int(parsed)


def _normalize_finite_range(value: Any, min_value: float, max_value: float) -> float | None:
    parsed = as_finite_number(value)
    if parsed is None or parsed < min_value or parsed > max_value:
        return None
    return parsed


def _normalize_integer_range(value: Any, min_value: int, max_value: int) -> int | None:
    parsed = as_finite_number(value)
    if parsed is None or not float(parsed).is_integer() or parsed < min_value or parsed > max_value:
        return None
    return int(parsed)


def normalize_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = _read_nested_elevenlabs_config(config)
    return {
        "apiKey": normalize_secret_input_string(raw.get("apiKey")),
        "baseUrl": normalize_optional_string(raw.get("baseUrl")),
        "modelId": normalize_optional_string(
            raw.get("modelId") or raw.get("model") or raw.get("sttModel")
        ),
        "audioFormat": normalize_optional_string(
            raw.get("audioFormat") or raw.get("audio_format") or raw.get("encoding")
        ),
        "sampleRate": _normalize_positive_safe_integer(raw.get("sampleRate") or raw.get("sample_rate")),
        "languageCode": normalize_optional_string(raw.get("languageCode") or raw.get("language")),
        "commitStrategy": _normalize_commit_strategy(
            raw.get("commitStrategy") or raw.get("commit_strategy")
        ),
        "vadSilenceThresholdSecs": _normalize_finite_range(
            raw.get("vadSilenceThresholdSecs") or raw.get("vad_silence_threshold_secs"),
            0.3,
            3,
        ),
        "vadThreshold": _normalize_finite_range(
            raw.get("vadThreshold") or raw.get("vad_threshold"),
            0.1,
            0.9,
        ),
        "minSpeechDurationMs": _normalize_integer_range(
            raw.get("minSpeechDurationMs") or raw.get("min_speech_duration_ms"),
            50,
            2_000,
        ),
        "minSilenceDurationMs": _normalize_integer_range(
            raw.get("minSilenceDurationMs") or raw.get("min_silence_duration_ms"),
            50,
            2_000,
        ),
    }


def _normalize_elevenlabs_realtime_base_url(value: str | None = None) -> str:
    parsed = urlparse(normalize_elevenlabs_base_url(value))
    scheme = "ws" if parsed.scheme == "http" else "wss"
    return urlunparse(
        (
            scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            "",
            "",
        )
    )


def to_eleven_labs_realtime_ws_url(config: dict[str, Any]) -> str:
    parsed = urlparse(
        f"{_normalize_elevenlabs_realtime_base_url(config['baseUrl'])}/v1/speech-to-text/realtime"
    )
    query: dict[str, str] = {
        "model_id": config["modelId"],
        "audio_format": config["audioFormat"],
        "commit_strategy": config["commitStrategy"],
        "include_timestamps": "false",
        "include_language_detection": "false",
    }
    language_code = normalize_optional_string(config.get("languageCode"))
    if language_code:
        query["language_code"] = language_code
    if config.get("vadSilenceThresholdSecs") is not None:
        query["vad_silence_threshold_secs"] = str(config["vadSilenceThresholdSecs"])
    if config.get("vadThreshold") is not None:
        query["vad_threshold"] = str(config["vadThreshold"])
    if config.get("minSpeechDurationMs") is not None:
        query["min_speech_duration_ms"] = str(config["minSpeechDurationMs"])
    if config.get("minSilenceDurationMs") is not None:
        query["min_silence_duration_ms"] = str(config["minSilenceDurationMs"])
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def _read_error_detail(event: dict[str, Any]) -> str:
    return (
        normalize_optional_string(event.get("error"))
        or normalize_optional_string(event.get("message"))
        or normalize_optional_string(event.get("code"))
        or "ElevenLabs realtime transcription error"
    )


def _create_eleven_labs_realtime_transcription_session(config: dict[str, Any]) -> Any:
    last_transcript: str | None = None

    def emit_transcript(text: str) -> None:
        nonlocal last_transcript
        if text == last_transcript:
            return
        last_transcript = text
        on_transcript = config.get("onTranscript")
        if callable(on_transcript):
            on_transcript(text)

    def send_audio_chunk(audio: bytes, transport: Any) -> None:
        payload: dict[str, Any] = {
            "message_type": "input_audio_chunk",
            "audio_base_64": base64.b64encode(audio).decode("ascii"),
            "sample_rate": config["sampleRate"],
        }
        if config["commitStrategy"] == "manual":
            payload["commit"] = True
        transport.send_json(payload)

    def handle_event(event: dict[str, Any], transport: Any) -> None:
        message_type = event.get("message_type")
        if message_type == "session_started":
            transport.mark_ready()
            return
        if not transport.is_ready() and isinstance(message_type, str) and "error" in message_type:
            transport.fail_connect(RuntimeError(_read_error_detail(event)))
            return
        if message_type == "partial_transcript":
            text = event.get("text")
            if text:
                on_partial = config.get("onPartial")
                if callable(on_partial):
                    on_partial(text)
            return
        if message_type in {"committed_transcript", "committed_transcript_with_timestamps"}:
            text = event.get("text")
            if text:
                emit_transcript(text)
            return
        if isinstance(message_type, str) and "error" in message_type:
            on_error = config.get("onError")
            if callable(on_error):
                on_error(RuntimeError(_read_error_detail(event)))

    return create_realtime_transcription_websocket_session(
        {
            "providerId": "elevenlabs",
            "callbacks": config,
            "url": lambda: to_eleven_labs_realtime_ws_url(config),
            "headers": {"xi-api-key": config["apiKey"]},
            "connectTimeoutMs": ELEVENLABS_REALTIME_CONNECT_TIMEOUT_MS,
            "closeTimeoutMs": ELEVENLABS_REALTIME_CLOSE_TIMEOUT_MS,
            "maxReconnectAttempts": ELEVENLABS_REALTIME_MAX_RECONNECT_ATTEMPTS,
            "reconnectDelayMs": ELEVENLABS_REALTIME_RECONNECT_DELAY_MS,
            "maxQueuedBytes": ELEVENLABS_REALTIME_MAX_QUEUED_BYTES,
            "connectTimeoutMessage": "ElevenLabs realtime transcription connection timeout",
            "reconnectLimitMessage": "ElevenLabs realtime transcription reconnect limit reached",
            "sendAudio": send_audio_chunk,
            "onClose": lambda transport: transport.send_json(
                {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "sample_rate": config["sampleRate"],
                    "commit": True,
                }
            ),
            "onMessage": handle_event,
        }
    )


def build_eleven_labs_realtime_transcription_provider() -> dict[str, Any]:
    def resolve_config(params: dict[str, Any]) -> dict[str, Any]:
        raw_config = params.get("rawConfig") if isinstance(params.get("rawConfig"), dict) else {}
        return normalize_provider_config(raw_config)

    def is_configured(params: dict[str, Any]) -> bool:
        provider_config = (
            params.get("providerConfig") if isinstance(params.get("providerConfig"), dict) else {}
        )
        return bool(
            normalize_provider_config(provider_config).get("apiKey")
            or resolve_eleven_labs_api_key_with_profile_fallback()
            or os.environ.get("XI_API_KEY")
        )

    def create_session(req: dict[str, Any]) -> Any:
        provider_config = req.get("providerConfig") if isinstance(req.get("providerConfig"), dict) else {}
        config = normalize_provider_config(provider_config)
        api_key = (
            config.get("apiKey")
            or resolve_eleven_labs_api_key_with_profile_fallback()
            or os.environ.get("XI_API_KEY")
        )
        if not api_key:
            raise RuntimeError("ElevenLabs API key missing")
        return _create_eleven_labs_realtime_transcription_session(
            {
                **req,
                "apiKey": api_key,
                "baseUrl": normalize_elevenlabs_base_url(config.get("baseUrl")),
                "modelId": config.get("modelId") or ELEVENLABS_REALTIME_DEFAULT_MODEL,
                "audioFormat": config.get("audioFormat") or ELEVENLABS_REALTIME_DEFAULT_AUDIO_FORMAT,
                "sampleRate": config.get("sampleRate") or ELEVENLABS_REALTIME_DEFAULT_SAMPLE_RATE,
                "commitStrategy": config.get("commitStrategy")
                or ELEVENLABS_REALTIME_DEFAULT_COMMIT_STRATEGY,
                "languageCode": config.get("languageCode"),
                "vadSilenceThresholdSecs": config.get("vadSilenceThresholdSecs"),
                "vadThreshold": config.get("vadThreshold"),
                "minSpeechDurationMs": config.get("minSpeechDurationMs"),
                "minSilenceDurationMs": config.get("minSilenceDurationMs"),
            }
        )

    return {
        "id": "elevenlabs",
        "label": "ElevenLabs Realtime Transcription",
        "aliases": ["elevenlabs-realtime", "scribe-v2-realtime"],
        "defaultModel": ELEVENLABS_REALTIME_DEFAULT_MODEL,
        "autoSelectOrder": 40,
        "resolveConfig": resolve_config,
        "isConfigured": is_configured,
        "createSession": create_session,
    }


testing = {
    "normalizeProviderConfig": normalize_provider_config,
    "toElevenLabsRealtimeWsUrl": to_eleven_labs_realtime_ws_url,
}
__testing__ = testing
