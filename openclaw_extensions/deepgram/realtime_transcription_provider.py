import os
import urllib.parse
from typing import Any, Optional

from .._sdk import normalize_secret_input
from .audio import DEFAULT_DEEPGRAM_AUDIO_BASE_URL, DEFAULT_DEEPGRAM_AUDIO_MODEL

DEEPGRAM_REALTIME_DEFAULT_SAMPLE_RATE = 8000
DEEPGRAM_REALTIME_DEFAULT_ENCODING = "mulaw"
DEEPGRAM_REALTIME_DEFAULT_ENDPOINTING_MS = 800
DEEPGRAM_REALTIME_CONNECT_TIMEOUT_MS = 10000
DEEPGRAM_REALTIME_CLOSE_TIMEOUT_MS = 5000
DEEPGRAM_REALTIME_MAX_RECONNECT_ATTEMPTS = 5
DEEPGRAM_REALTIME_RECONNECT_DELAY_MS = 1000
DEEPGRAM_REALTIME_MAX_QUEUED_BYTES = 2 * 1024 * 1024

_ValidEncodings = {"linear16", "mulaw", "alaw"}


def _read_record(value: Any) -> Optional[dict]:
    if isinstance(value, dict):
        return value
    return None


def _normalize_optional_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _read_boolean(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return None


def _read_finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value == value:
        return value
    return None


def _normalize_deepgram_encoding(value: Any) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if not normalized:
        return None
    lowered = normalized.lower()
    if lowered in ("pcm", "pcm_s16le", "linear16"):
        return "linear16"
    if lowered in ("ulaw", "g711_ulaw", "g711-mulaw"):
        return "mulaw"
    if lowered in ("g711_alaw", "g711-alaw"):
        return "alaw"
    if lowered in _ValidEncodings:
        return lowered
    raise RuntimeError(f"Invalid Deepgram realtime transcription encoding: {lowered}")


def _read_nested_deepgram_config(raw_config: Any) -> dict:
    raw = _read_record(raw_config) or {}
    providers = _read_record(raw.get("providers")) or {}
    nested = _read_record(providers.get("deepgram")) or _read_record(raw.get("deepgram")) or raw
    return nested if isinstance(nested, dict) else {}


def _normalize_deepgram_realtime_base_url(value: Any) -> str:
    resolved = _normalize_optional_string(value)
    if not resolved:
        resolved = _normalize_optional_string(os.environ.get("DEEPGRAM_BASE_URL"))
    if resolved:
        return resolved
    return DEFAULT_DEEPGRAM_AUDIO_BASE_URL


def _to_deepgram_realtime_ws_url(config: dict) -> str:
    base_url = _normalize_deepgram_realtime_base_url(config.get("baseUrl"))
    parsed = urllib.parse.urlparse(base_url)
    scheme = "ws" if parsed.scheme == "http" else "wss"
    path = parsed.path.rstrip("/")
    pathname = f"{path}/listen"
    query_parts = [
        ("model", config["model"]),
        ("encoding", config["encoding"]),
        ("sample_rate", str(config["sampleRate"])),
        ("channels", "1"),
        ("interim_results", str(config["interimResults"]).lower()),
        ("endpointing", str(config["endpointingMs"])),
    ]
    if config.get("language"):
        query_parts.append(("language", config["language"]))
    query_string = urllib.parse.urlencode(query_parts)
    return urllib.parse.urlunparse((scheme, parsed.netloc, pathname, "", query_string, ""))


def _normalize_provider_config(config: Any) -> dict:
    raw = _read_nested_deepgram_config(config)
    model_value = raw.get("model")
    if model_value is None:
        model_value = raw.get("sttModel")
    endpointing_value = raw.get("endpointingMs")
    if endpointing_value is None:
        endpointing_value = raw.get("endpointing")
    if endpointing_value is None:
        endpointing_value = raw.get("silenceDurationMs")
    interim_value = raw.get("interimResults")
    if interim_value is None:
        interim_value = raw.get("interim_results")
    sample_rate_value = raw.get("sampleRate")
    if sample_rate_value is None:
        sample_rate_value = raw.get("sample_rate")
    return {
        "apiKey": normalize_secret_input(raw.get("apiKey")),
        "baseUrl": _normalize_optional_string(raw.get("baseUrl")),
        "model": _normalize_optional_string(model_value),
        "language": _normalize_optional_string(raw.get("language")),
        "sampleRate": _read_finite_number(sample_rate_value),
        "encoding": _normalize_deepgram_encoding(raw.get("encoding")),
        "interimResults": _read_boolean(interim_value),
        "endpointingMs": _read_finite_number(endpointing_value),
    }


def _read_error_detail(value: Any) -> str:
    if isinstance(value, str):
        return value
    record = _read_record(value) or {}
    message = _normalize_optional_string(record.get("message"))
    code = _normalize_optional_string(record.get("code"))
    return message or code or "Deepgram realtime transcription error"


def _read_transcript_text(event: dict) -> Optional[str]:
    channel = _read_record(event.get("channel")) if isinstance(event, dict) else None
    if not channel:
        return None
    alternatives = channel.get("alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        return None
    alternative = _read_record(alternatives[0]) if alternatives else None
    if not alternative:
        return None
    return _normalize_optional_string(alternative.get("transcript"))


class _DeepgramRealtimeSession:
    def __init__(self, config: dict) -> None:
        self._config = config
        self._last_transcript: Optional[str] = None
        self._speech_started = False
        self._closed = False

    async def start(self) -> None:
        pass

    async def send_audio(self, audio: bytes) -> None:
        pass

    async def close(self) -> None:
        self._closed = True

    def handle_event(self, event: Any) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "Results":
            text = _read_transcript_text(event)
            if not text:
                return
            if not self._speech_started:
                self._speech_started = True
                on_speech_start = self._config.get("onSpeechStart")
                if on_speech_start:
                    on_speech_start()
            if event.get("is_final") or event.get("speech_final"):
                if text != self._last_transcript:
                    self._last_transcript = text
                on_transcript = self._config.get("onTranscript")
                if on_transcript:
                    on_transcript(text)
                if event.get("speech_final"):
                    self._speech_started = False
                return
            on_partial = self._config.get("onPartial")
            if on_partial:
                on_partial(text)
            return
        if event_type == "SpeechStarted":
            self._speech_started = True
            on_speech_start = self._config.get("onSpeechStart")
            if on_speech_start:
                on_speech_start()
            return
        if event_type in ("Error", "error"):
            on_error = self._config.get("onError")
            if on_error:
                on_error(RuntimeError(_read_error_detail(event.get("error") or event.get("message"))))


def _create_deepgram_realtime_transcription_session(config: dict) -> _DeepgramRealtimeSession:
    return _DeepgramRealtimeSession(config)


def build_deepgram_realtime_transcription_provider() -> dict:
    def resolve_config(ctx: dict) -> dict:
        return _normalize_provider_config(ctx.get("rawConfig", {}))

    def is_configured(ctx: dict) -> bool:
        provider_config = _normalize_provider_config(ctx.get("providerConfig", {}))
        return bool(provider_config.get("apiKey") or os.environ.get("DEEPGRAM_API_KEY"))

    def create_session(req: dict) -> _DeepgramRealtimeSession:
        config = _normalize_provider_config(req.get("providerConfig", {}))
        api_key = config.get("apiKey") or os.environ.get("DEEPGRAM_API_KEY")
        if not api_key:
            raise RuntimeError("Deepgram API key missing")
        interim_results = config.get("interimResults")
        if interim_results is None:
            interim_results = True
        endpointing = config.get("endpointingMs")
        if endpointing is None:
            endpointing = DEEPGRAM_REALTIME_DEFAULT_ENDPOINTING_MS
        sample_rate = config.get("sampleRate")
        if sample_rate is None:
            sample_rate = DEEPGRAM_REALTIME_DEFAULT_SAMPLE_RATE
        encoding = config.get("encoding") or DEEPGRAM_REALTIME_DEFAULT_ENCODING
        session_config = dict(req)
        session_config.update({
            "apiKey": api_key,
            "baseUrl": _normalize_deepgram_realtime_base_url(config.get("baseUrl")),
            "model": config.get("model") or DEFAULT_DEEPGRAM_AUDIO_MODEL,
            "sampleRate": sample_rate,
            "encoding": encoding,
            "interimResults": interim_results,
            "endpointingMs": endpointing,
            "language": config.get("language"),
        })
        return _create_deepgram_realtime_transcription_session(session_config)

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
    "normalizeProviderConfig": _normalize_provider_config,
    "toDeepgramRealtimeWsUrl": _to_deepgram_realtime_ws_url,
}
