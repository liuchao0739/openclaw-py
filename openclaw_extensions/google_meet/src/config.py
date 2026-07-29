"""Google Meet helper module supports config behavior."""

from __future__ import annotations

import math
import os
import re
from typing import Any

from openclaw.packages.normalization_core import (
    add_timer_timeout_grace_ms,
    as_record,
    normalize_optional_lowercase_string,
    normalize_optional_string,
    normalize_optional_trimmed_string_list,
    resolve_positive_timer_timeout_ms,
)

GoogleMeetTransport = str
GoogleMeetMode = str
GoogleMeetModeInput = str
GoogleMeetRealtimeStrategy = str
GoogleMeetChromeAudioFormat = str
GoogleMeetToolPolicy = str

REALTIME_VOICE_AGENT_CONSULT_TOOL_NAME = "openclaw_agent_consult"
_REALTIME_VOICE_AGENT_CONSULT_TOOL_POLICIES = ("safe-read-only", "owner", "none")

GOOGLE_MEET_CLIENT_ID_KEYS = ("OPENCLAW_GOOGLE_MEET_CLIENT_ID", "GOOGLE_MEET_CLIENT_ID")
GOOGLE_MEET_CLIENT_SECRET_KEYS = ("OPENCLAW_GOOGLE_MEET_CLIENT_SECRET", "GOOGLE_MEET_CLIENT_SECRET")
GOOGLE_MEET_REFRESH_TOKEN_KEYS = ("OPENCLAW_GOOGLE_MEET_REFRESH_TOKEN", "GOOGLE_MEET_REFRESH_TOKEN")
GOOGLE_MEET_ACCESS_TOKEN_KEYS = ("OPENCLAW_GOOGLE_MEET_ACCESS_TOKEN", "GOOGLE_MEET_ACCESS_TOKEN")
GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT_KEYS = (
    "OPENCLAW_GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT",
    "GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT",
)
GOOGLE_MEET_DEFAULT_MEETING_KEYS = ("OPENCLAW_GOOGLE_MEET_DEFAULT_MEETING", "GOOGLE_MEET_DEFAULT_MEETING")
GOOGLE_MEET_PREVIEW_ACK_KEYS = ("OPENCLAW_GOOGLE_MEET_PREVIEW_ACK", "GOOGLE_MEET_PREVIEW_ACK")

SOX_DEFAULT_BUFFER_BYTES = 8192
SOX_MIN_BUFFER_BYTES = 17
DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES = SOX_DEFAULT_BUFFER_BYTES // 2
PLAIN_DECIMAL_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")

DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE = [
    "sox", "-q", "-t", "coreaudio", "BlackHole 2ch",
    "-t", "raw", "-r", "24000", "-c", "1",
    "-e", "signed-integer", "-b", "16", "-L", "-",
]
DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE = [
    "sox", "-q", "-t", "raw", "-r", "24000", "-c", "1",
    "-e", "signed-integer", "-b", "16", "-L", "-",
    "-t", "coreaudio", "BlackHole 2ch",
]
LEGACY_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE = [
    "rec", "-q", "-t", "raw", "-r", "8000", "-c", "1",
    "-e", "mu-law", "-b", "8", "-",
]
LEGACY_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE = [
    "play", "-q", "-t", "raw", "-r", "8000", "-c", "1",
    "-e", "mu-law", "-b", "8", "-",
]

DEFAULT_GOOGLE_MEET_CHROME_AUDIO_FORMAT = "pcm16-24khz"
DEFAULT_GOOGLE_MEET_BARGE_IN_RMS_THRESHOLD = 650
DEFAULT_GOOGLE_MEET_BARGE_IN_PEAK_THRESHOLD = 2500
DEFAULT_GOOGLE_MEET_BARGE_IN_COOLDOWN_MS = 900

DEFAULT_GOOGLE_MEET_REALTIME_INSTRUCTIONS = (
    "You are joining a private Google Meet as an OpenClaw voice transport. "
    "Keep spoken replies brief and natural. In agent mode, wait for OpenClaw "
    "consult results and speak them exactly. In bidi mode, answer directly "
    f"and call {REALTIME_VOICE_AGENT_CONSULT_TOOL_NAME} for deeper reasoning, "
    "current information, or tools."
)
DEFAULT_GOOGLE_MEET_REALTIME_INTRO_MESSAGE = "Say exactly: I'm here and listening."

DEFAULT_GOOGLE_MEET_CONFIG: dict[str, Any] = {
    "enabled": True,
    "defaults": {},
    "preview": {"enrollmentAcknowledged": False},
    "defaultTransport": "chrome",
    "defaultMode": "agent",
    "chrome": {
        "audioBackend": "blackhole-2ch",
        "audioFormat": DEFAULT_GOOGLE_MEET_CHROME_AUDIO_FORMAT,
        "audioBufferBytes": DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES,
        "launch": True,
        "guestName": "OpenClaw Agent",
        "reuseExistingTab": True,
        "autoJoin": True,
        "joinTimeoutMs": 30_000,
        "waitForInCallMs": 20_000,
        "audioInputCommand": list(DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND),
        "audioOutputCommand": list(DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND),
        "bargeInRmsThreshold": DEFAULT_GOOGLE_MEET_BARGE_IN_RMS_THRESHOLD,
        "bargeInPeakThreshold": DEFAULT_GOOGLE_MEET_BARGE_IN_PEAK_THRESHOLD,
        "bargeInCooldownMs": DEFAULT_GOOGLE_MEET_BARGE_IN_COOLDOWN_MS,
    },
    "chromeNode": {},
    "twilio": {},
    "voiceCall": {
        "enabled": True,
        "requestTimeoutMs": 30_000,
        "dtmfDelayMs": 12_000,
        "postDtmfSpeechDelayMs": 5_000,
    },
    "realtime": {
        "strategy": "agent",
        "provider": "openai",
        "transcriptionProvider": "openai",
        "instructions": DEFAULT_GOOGLE_MEET_REALTIME_INSTRUCTIONS,
        "introMessage": DEFAULT_GOOGLE_MEET_REALTIME_INTRO_MESSAGE,
        "toolPolicy": "safe-read-only",
        "providers": {},
    },
    "oauth": {},
    "auth": {"provider": "google-oauth"},
}


def _with_sox_buffer(command: list[str], buffer_bytes: int) -> list[str]:
    return [command[0] or "sox", "-q", "--buffer", str(buffer_bytes), *command[2:]]


DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND = _with_sox_buffer(
    DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE, DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES
)
DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND = _with_sox_buffer(
    DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE, DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES
)


def resolve_realtime_voice_agent_consult_tool_policy(value: Any, fallback: str) -> str:
    normalized = normalize_optional_lowercase_string(value)
    if normalized in _REALTIME_VOICE_AGENT_CONSULT_TOOL_POLICIES:
        return normalized
    return fallback


def resolve_google_meet_gateway_operation_timeout_ms(config: dict[str, Any]) -> int:
    return max(
        60_000,
        add_timer_timeout_grace_ms(config["chrome"]["joinTimeoutMs"], 30_000) or 1,
        add_timer_timeout_grace_ms(config["voiceCall"]["requestTimeoutMs"], 10_000) or 1,
    )


def _resolve_boolean(value: Any, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


def _resolve_number(value: Any, fallback: int) -> int:
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return value
    return fallback


def _resolve_timer_config_ms(value: Any, fallback: int) -> int:
    return resolve_positive_timer_timeout_ms(_resolve_number(value, fallback), fallback)


def _resolve_optional_number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    if isinstance(value, str) and value.strip():
        trimmed = value.strip()
        parsed = float(trimmed) if PLAIN_DECIMAL_NUMBER_RE.match(trimmed) else float("nan")
        return parsed if math.isfinite(parsed) else None
    return None


def _read_env_string(env: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = normalize_optional_string(env.get(key))
        if value:
            return value
    return None


def _normalize_string_allow_empty(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) else None


def _read_env_boolean(env: dict[str, str], keys: tuple[str, ...]) -> bool | None:
    normalized = normalize_optional_lowercase_string(_read_env_string(env, keys))
    if not normalized:
        return None
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return None


def _read_env_number(env: dict[str, str], keys: tuple[str, ...]) -> int | float | None:
    return _resolve_optional_number(_read_env_string(env, keys))


def _resolve_string_array(value: Any) -> list[str] | None:
    return normalize_optional_trimmed_string_list(value)


def _resolve_providers_config(value: Any) -> dict[str, dict[str, Any]]:
    raw = as_record(value)
    providers: dict[str, dict[str, Any]] = {}
    for key, entry in raw.items():
        provider_id = normalize_optional_lowercase_string(key)
        if not provider_id:
            continue
        providers[provider_id] = as_record(entry)
    return providers


def _resolve_transport(value: Any, fallback: str) -> str:
    normalized = normalize_optional_lowercase_string(value)
    if normalized in ("chrome", "chrome-node", "twilio"):
        return normalized
    return fallback


def _resolve_mode(value: Any, fallback: str) -> str:
    normalized = normalize_optional_lowercase_string(value)
    if normalized == "realtime":
        return "agent"
    if normalized in ("agent", "bidi", "transcribe"):
        return normalized
    return fallback


def _resolve_realtime_strategy(value: Any, fallback: str) -> str:
    normalized = normalize_optional_lowercase_string(value)
    if normalized in ("agent", "bidi"):
        return normalized
    return fallback


def _resolve_chrome_audio_format(value: Any) -> str | None:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.lower().replace("_", "-")
    if normalized in ("pcm16-24khz", "pcm16-24k", "pcm24", "pcm"):
        return "pcm16-24khz"
    if normalized in ("g711-ulaw-8khz", "g711-ulaw-8k", "g711-ulaw", "mulaw", "mu-law"):
        return "g711-ulaw-8khz"
    return None


def _resolve_audio_buffer_bytes(value: Any, fallback: int) -> int:
    number = _resolve_number(value, fallback)
    if not math.isfinite(number) or number <= 0:
        return fallback
    return max(SOX_MIN_BUFFER_BYTES, int(number))


def _default_audio_input_command(fmt: str, buffer_bytes: int) -> list[str]:
    base = (
        LEGACY_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE
        if fmt == "g711-ulaw-8khz"
        else DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE
    )
    return _with_sox_buffer(base, buffer_bytes)


def _default_audio_output_command(fmt: str, buffer_bytes: int) -> list[str]:
    base = (
        LEGACY_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE
        if fmt == "g711-ulaw-8khz"
        else DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE
    )
    return _with_sox_buffer(base, buffer_bytes)


def resolve_google_meet_config(input_value: Any) -> dict[str, Any]:
    return resolve_google_meet_config_with_env(input_value)


def resolve_google_meet_config_with_env(
    input_value: Any,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = env if env is not None else dict(os.environ)
    raw = as_record(input_value)
    defaults = as_record(raw.get("defaults"))
    preview = as_record(raw.get("preview"))
    chrome = as_record(raw.get("chrome"))
    configured_audio_input_command = _resolve_string_array(chrome.get("audioInputCommand"))
    configured_audio_output_command = _resolve_string_array(chrome.get("audioOutputCommand"))
    has_custom_audio_command = (
        configured_audio_input_command is not None
        or configured_audio_output_command is not None
    )
    audio_format = _resolve_chrome_audio_format(chrome.get("audioFormat")) or (
        "g711-ulaw-8khz"
        if has_custom_audio_command
        else DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["audioFormat"]
    )
    audio_buffer_bytes = _resolve_audio_buffer_bytes(
        chrome.get("audioBufferBytes"),
        DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["audioBufferBytes"],
    )
    chrome_node = as_record(raw.get("chromeNode"))
    twilio = as_record(raw.get("twilio"))
    voice_call = as_record(raw.get("voiceCall"))
    realtime = as_record(raw.get("realtime"))
    realtime_provider = normalize_optional_string(realtime.get("provider"))
    resolved_realtime_provider = (
        realtime_provider or DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["provider"]
    )
    oauth = as_record(raw.get("oauth"))
    auth = as_record(raw.get("auth"))

    return {
        "enabled": _resolve_boolean(raw.get("enabled"), DEFAULT_GOOGLE_MEET_CONFIG["enabled"]),
        "defaults": {
            "meeting": normalize_optional_string(defaults.get("meeting"))
            or _read_env_string(env, GOOGLE_MEET_DEFAULT_MEETING_KEYS),
        },
        "preview": {
            "enrollmentAcknowledged": _resolve_boolean(
                preview.get("enrollmentAcknowledged"),
                _read_env_boolean(env, GOOGLE_MEET_PREVIEW_ACK_KEYS)
                or DEFAULT_GOOGLE_MEET_CONFIG["preview"]["enrollmentAcknowledged"],
            ),
        },
        "defaultTransport": _resolve_transport(
            raw.get("defaultTransport"), DEFAULT_GOOGLE_MEET_CONFIG["defaultTransport"]
        ),
        "defaultMode": _resolve_mode(raw.get("defaultMode"), DEFAULT_GOOGLE_MEET_CONFIG["defaultMode"]),
        "chrome": {
            "audioBackend": "blackhole-2ch",
            "audioFormat": audio_format,
            "audioBufferBytes": audio_buffer_bytes,
            "launch": _resolve_boolean(chrome.get("launch"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["launch"]),
            "browserProfile": normalize_optional_string(chrome.get("browserProfile")),
            "guestName": normalize_optional_string(chrome.get("guestName"))
            or DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["guestName"],
            "reuseExistingTab": _resolve_boolean(
                chrome.get("reuseExistingTab"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["reuseExistingTab"]
            ),
            "autoJoin": _resolve_boolean(chrome.get("autoJoin"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["autoJoin"]),
            "joinTimeoutMs": _resolve_timer_config_ms(
                chrome.get("joinTimeoutMs"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["joinTimeoutMs"]
            ),
            "waitForInCallMs": _resolve_timer_config_ms(
                chrome.get("waitForInCallMs"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["waitForInCallMs"]
            ),
            "audioInputCommand": configured_audio_input_command
            or _default_audio_input_command(audio_format, audio_buffer_bytes),
            "audioOutputCommand": configured_audio_output_command
            or _default_audio_output_command(audio_format, audio_buffer_bytes),
            "bargeInInputCommand": _resolve_string_array(chrome.get("bargeInInputCommand")),
            "bargeInRmsThreshold": _resolve_number(
                chrome.get("bargeInRmsThreshold"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["bargeInRmsThreshold"]
            ),
            "bargeInPeakThreshold": _resolve_number(
                chrome.get("bargeInPeakThreshold"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["bargeInPeakThreshold"]
            ),
            "bargeInCooldownMs": _resolve_timer_config_ms(
                chrome.get("bargeInCooldownMs"), DEFAULT_GOOGLE_MEET_CONFIG["chrome"]["bargeInCooldownMs"]
            ),
            "audioBridgeCommand": _resolve_string_array(chrome.get("audioBridgeCommand")),
            "audioBridgeHealthCommand": _resolve_string_array(chrome.get("audioBridgeHealthCommand")),
        },
        "chromeNode": {"node": normalize_optional_string(chrome_node.get("node"))},
        "twilio": {
            "defaultDialInNumber": normalize_optional_string(twilio.get("defaultDialInNumber")),
            "defaultPin": normalize_optional_string(twilio.get("defaultPin")),
            "defaultDtmfSequence": normalize_optional_string(twilio.get("defaultDtmfSequence")),
        },
        "voiceCall": {
            "enabled": _resolve_boolean(voice_call.get("enabled"), DEFAULT_GOOGLE_MEET_CONFIG["voiceCall"]["enabled"]),
            "gatewayUrl": normalize_optional_string(voice_call.get("gatewayUrl")),
            "token": normalize_optional_string(voice_call.get("token")),
            "requestTimeoutMs": _resolve_timer_config_ms(
                voice_call.get("requestTimeoutMs"), DEFAULT_GOOGLE_MEET_CONFIG["voiceCall"]["requestTimeoutMs"]
            ),
            "dtmfDelayMs": _resolve_timer_config_ms(
                voice_call.get("dtmfDelayMs"), DEFAULT_GOOGLE_MEET_CONFIG["voiceCall"]["dtmfDelayMs"]
            ),
            "postDtmfSpeechDelayMs": _resolve_timer_config_ms(
                voice_call.get("postDtmfSpeechDelayMs"),
                DEFAULT_GOOGLE_MEET_CONFIG["voiceCall"]["postDtmfSpeechDelayMs"],
            ),
            "introMessage": normalize_optional_string(voice_call.get("introMessage")),
        },
        "realtime": {
            "strategy": _resolve_realtime_strategy(
                realtime.get("strategy"), DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["strategy"]
            ),
            "provider": resolved_realtime_provider,
            "transcriptionProvider": normalize_optional_string(realtime.get("transcriptionProvider"))
            or (
                resolved_realtime_provider
                if realtime_provider and realtime_provider != "google"
                else DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["transcriptionProvider"]
            ),
            "voiceProvider": normalize_optional_string(realtime.get("voiceProvider")),
            "model": normalize_optional_string(realtime.get("model"))
            or DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["model"],
            "instructions": normalize_optional_string(realtime.get("instructions"))
            or DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["instructions"],
            "introMessage": _normalize_string_allow_empty(realtime.get("introMessage"))
            or DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["introMessage"],
            "agentId": normalize_optional_string(realtime.get("agentId")),
            "toolPolicy": resolve_realtime_voice_agent_consult_tool_policy(
                realtime.get("toolPolicy"), DEFAULT_GOOGLE_MEET_CONFIG["realtime"]["toolPolicy"]
            ),
            "providers": _resolve_providers_config(realtime.get("providers")),
        },
        "oauth": {
            "clientId": normalize_optional_string(oauth.get("clientId"))
            or normalize_optional_string(auth.get("clientId"))
            or _read_env_string(env, GOOGLE_MEET_CLIENT_ID_KEYS),
            "clientSecret": normalize_optional_string(oauth.get("clientSecret"))
            or normalize_optional_string(auth.get("clientSecret"))
            or _read_env_string(env, GOOGLE_MEET_CLIENT_SECRET_KEYS),
            "refreshToken": normalize_optional_string(oauth.get("refreshToken"))
            or _read_env_string(env, GOOGLE_MEET_REFRESH_TOKEN_KEYS),
            "accessToken": normalize_optional_string(oauth.get("accessToken"))
            or _read_env_string(env, GOOGLE_MEET_ACCESS_TOKEN_KEYS),
            "expiresAt": _resolve_optional_number(oauth.get("expiresAt"))
            or _read_env_number(env, GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT_KEYS),
        },
        "auth": {
            "provider": "google-oauth",
            "clientId": normalize_optional_string(auth.get("clientId")),
            "clientSecret": normalize_optional_string(auth.get("clientSecret")),
            "tokenPath": normalize_optional_string(auth.get("tokenPath")),
        },
    }
