"""Google Meet plugin configuration resolution."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from openclaw.packages.normalization_core import (
    add_timer_timeout_grace_ms,
    as_record,
    normalize_optional_lowercase_string,
    normalize_optional_string,
    normalize_optional_trimmed_string_list,
    resolve_positive_timer_timeout_ms,
)

REALTIME_VOICE_AGENT_CONSULT_TOOL_NAME = "openclaw_agent_consult"
REALTIME_VOICE_AGENT_CONSULT_TOOL_POLICIES = ("safe-read-only", "owner", "none")
GoogleMeetTransport = Literal["chrome", "chrome-node", "twilio"]
GoogleMeetMode = Literal["agent", "bidi", "transcribe"]
GoogleMeetModeInput = Literal["agent", "bidi", "transcribe", "realtime"]
GoogleMeetRealtimeStrategy = Literal["agent", "bidi"]
GoogleMeetChromeAudioFormat = Literal["pcm16-24khz", "g711-ulaw-8khz"]
GoogleMeetToolPolicy = Literal["safe-read-only", "owner", "none"]

SOX_DEFAULT_BUFFER_BYTES = 8192
SOX_MIN_BUFFER_BYTES = 17
DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES = SOX_DEFAULT_BUFFER_BYTES // 2
PLAIN_DECIMAL_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")

DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE = [
    "sox",
    "-q",
    "-t",
    "coreaudio",
    "BlackHole 2ch",
    "-t",
    "raw",
    "-r",
    "24000",
    "-c",
    "1",
    "-e",
    "signed-integer",
    "-b",
    "16",
    "-L",
    "-",
]
DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE = [
    "sox",
    "-q",
    "-t",
    "raw",
    "-r",
    "24000",
    "-c",
    "1",
    "-e",
    "signed-integer",
    "-b",
    "16",
    "-L",
    "-",
    "-t",
    "coreaudio",
    "BlackHole 2ch",
]
LEGACY_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE = [
    "rec",
    "-q",
    "-t",
    "raw",
    "-r",
    "8000",
    "-c",
    "1",
    "-e",
    "mu-law",
    "-b",
    "8",
    "-",
]
LEGACY_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE = [
    "play",
    "-q",
    "-t",
    "raw",
    "-r",
    "8000",
    "-c",
    "1",
    "-e",
    "mu-law",
    "-b",
    "8",
    "-",
]

DEFAULT_GOOGLE_MEET_CHROME_AUDIO_FORMAT: GoogleMeetChromeAudioFormat = "pcm16-24khz"
DEFAULT_GOOGLE_MEET_BARGE_IN_RMS_THRESHOLD = 650
DEFAULT_GOOGLE_MEET_BARGE_IN_PEAK_THRESHOLD = 2500
DEFAULT_GOOGLE_MEET_BARGE_IN_COOLDOWN_MS = 900

DEFAULT_GOOGLE_MEET_REALTIME_INSTRUCTIONS = (
    "You are joining a private Google Meet as an OpenClaw voice transport. "
    "Keep spoken replies brief and natural. In agent mode, wait for OpenClaw consult results "
    "and speak them exactly. In bidi mode, answer directly and call "
    f"{REALTIME_VOICE_AGENT_CONSULT_TOOL_NAME} for deeper reasoning, current information, or tools."
)
DEFAULT_GOOGLE_MEET_REALTIME_INTRO_MESSAGE = "Say exactly: I'm here and listening."

GOOGLE_MEET_CLIENT_ID_KEYS = ("OPENCLAW_GOOGLE_MEET_CLIENT_ID", "GOOGLE_MEET_CLIENT_ID")
GOOGLE_MEET_CLIENT_SECRET_KEYS = (
    "OPENCLAW_GOOGLE_MEET_CLIENT_SECRET",
    "GOOGLE_MEET_CLIENT_SECRET",
)
GOOGLE_MEET_REFRESH_TOKEN_KEYS = (
    "OPENCLAW_GOOGLE_MEET_REFRESH_TOKEN",
    "GOOGLE_MEET_REFRESH_TOKEN",
)
GOOGLE_MEET_ACCESS_TOKEN_KEYS = (
    "OPENCLAW_GOOGLE_MEET_ACCESS_TOKEN",
    "GOOGLE_MEET_ACCESS_TOKEN",
)
GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT_KEYS = (
    "OPENCLAW_GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT",
    "GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT",
)
GOOGLE_MEET_DEFAULT_MEETING_KEYS = (
    "OPENCLAW_GOOGLE_MEET_DEFAULT_MEETING",
    "GOOGLE_MEET_DEFAULT_MEETING",
)
GOOGLE_MEET_PREVIEW_ACK_KEYS = (
    "OPENCLAW_GOOGLE_MEET_PREVIEW_ACK",
    "GOOGLE_MEET_PREVIEW_ACK",
)


@dataclass
class GoogleMeetDefaultsConfig:
    meeting: str | None = None


@dataclass
class GoogleMeetPreviewConfig:
    enrollment_acknowledged: bool = False


@dataclass
class GoogleMeetChromeConfig:
    audio_backend: Literal["blackhole-2ch"] = "blackhole-2ch"
    audio_format: GoogleMeetChromeAudioFormat = DEFAULT_GOOGLE_MEET_CHROME_AUDIO_FORMAT
    audio_buffer_bytes: int = DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES
    launch: bool = True
    browser_profile: str | None = None
    guest_name: str = "OpenClaw Agent"
    reuse_existing_tab: bool = True
    auto_join: bool = True
    join_timeout_ms: int = 30_000
    wait_for_in_call_ms: int = 20_000
    audio_input_command: list[str] | None = None
    audio_output_command: list[str] | None = None
    barge_in_input_command: list[str] | None = None
    barge_in_rms_threshold: int = DEFAULT_GOOGLE_MEET_BARGE_IN_RMS_THRESHOLD
    barge_in_peak_threshold: int = DEFAULT_GOOGLE_MEET_BARGE_IN_PEAK_THRESHOLD
    barge_in_cooldown_ms: int = DEFAULT_GOOGLE_MEET_BARGE_IN_COOLDOWN_MS
    audio_bridge_command: list[str] | None = None
    audio_bridge_health_command: list[str] | None = None


@dataclass
class GoogleMeetChromeNodeConfig:
    node: str | None = None


@dataclass
class GoogleMeetTwilioConfig:
    default_dial_in_number: str | None = None
    default_pin: str | None = None
    default_dtmf_sequence: str | None = None


@dataclass
class GoogleMeetVoiceCallConfig:
    enabled: bool = True
    gateway_url: str | None = None
    token: str | None = None
    request_timeout_ms: int = 30_000
    dtmf_delay_ms: int = 12_000
    post_dtmf_speech_delay_ms: int = 5_000
    intro_message: str | None = None


@dataclass
class GoogleMeetRealtimeConfig:
    strategy: GoogleMeetRealtimeStrategy = "agent"
    provider: str | None = "openai"
    transcription_provider: str | None = "openai"
    voice_provider: str | None = None
    model: str | None = None
    instructions: str | None = None
    intro_message: str | None = DEFAULT_GOOGLE_MEET_REALTIME_INTRO_MESSAGE
    agent_id: str | None = None
    tool_policy: GoogleMeetToolPolicy = "safe-read-only"
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class GoogleMeetOAuthConfig:
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    access_token: str | None = None
    expires_at: float | None = None


@dataclass
class GoogleMeetAuthConfig:
    provider: Literal["google-oauth"] = "google-oauth"
    client_id: str | None = None
    client_secret: str | None = None
    token_path: str | None = None


@dataclass
class GoogleMeetConfig:
    enabled: bool = True
    defaults: GoogleMeetDefaultsConfig = field(default_factory=GoogleMeetDefaultsConfig)
    preview: GoogleMeetPreviewConfig = field(default_factory=GoogleMeetPreviewConfig)
    default_transport: GoogleMeetTransport = "chrome"
    default_mode: GoogleMeetMode = "agent"
    chrome: GoogleMeetChromeConfig = field(default_factory=GoogleMeetChromeConfig)
    chrome_node: GoogleMeetChromeNodeConfig = field(default_factory=GoogleMeetChromeNodeConfig)
    twilio: GoogleMeetTwilioConfig = field(default_factory=GoogleMeetTwilioConfig)
    voice_call: GoogleMeetVoiceCallConfig = field(default_factory=GoogleMeetVoiceCallConfig)
    realtime: GoogleMeetRealtimeConfig = field(default_factory=GoogleMeetRealtimeConfig)
    oauth: GoogleMeetOAuthConfig = field(default_factory=GoogleMeetOAuthConfig)
    auth: GoogleMeetAuthConfig = field(default_factory=GoogleMeetAuthConfig)


def _with_sox_buffer(command: list[str], buffer_bytes: int) -> list[str]:
    first = command[0] if command else "sox"
    return [first, "-q", "--buffer", str(buffer_bytes), *command[2:]]


DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND = _with_sox_buffer(
    list(DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE),
    DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES,
)
DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND = _with_sox_buffer(
    list(DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE),
    DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES,
)


def _is_realtime_voice_agent_consult_tool_policy(value: str | None) -> bool:
    return value in REALTIME_VOICE_AGENT_CONSULT_TOOL_POLICIES


def resolve_realtime_voice_agent_consult_tool_policy(
    value: Any,
    fallback: GoogleMeetToolPolicy,
) -> GoogleMeetToolPolicy:
    normalized = normalize_optional_lowercase_string(value)
    if _is_realtime_voice_agent_consult_tool_policy(normalized):
        return normalized
    return fallback


def resolve_google_meet_gateway_operation_timeout_ms(config: GoogleMeetConfig) -> int:
    return max(
        60_000,
        add_timer_timeout_grace_ms(config.chrome.join_timeout_ms, 30_000) or 1,
        add_timer_timeout_grace_ms(config.voice_call.request_timeout_ms, 10_000) or 1,
    )


def _resolve_boolean(value: Any, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


def _resolve_number(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)) and float(value) > 0 and float(value) != float("inf"):
        return float(value)
    return fallback


def _resolve_timer_config_ms(value: Any, fallback: float) -> int:
    return resolve_positive_timer_timeout_ms(_resolve_number(value, fallback), fallback)


def _resolve_optional_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and float(value) == float(value):
        return float(value)
    if isinstance(value, str) and value.strip():
        trimmed = value.strip()
        parsed = float(trimmed) if PLAIN_DECIMAL_NUMBER_RE.match(trimmed) else float("nan")
        return parsed if parsed == parsed else None
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
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _read_env_number(env: dict[str, str], keys: tuple[str, ...]) -> float | None:
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


def _resolve_transport(value: Any, fallback: GoogleMeetTransport) -> GoogleMeetTransport:
    normalized = normalize_optional_lowercase_string(value)
    if normalized in {"chrome", "chrome-node", "twilio"}:
        return normalized
    return fallback


def _resolve_mode(value: Any, fallback: GoogleMeetMode) -> GoogleMeetMode:
    normalized = normalize_optional_lowercase_string(value)
    if normalized == "realtime":
        return "agent"
    if normalized in {"agent", "bidi", "transcribe"}:
        return normalized
    return fallback


def _resolve_realtime_strategy(
    value: Any,
    fallback: GoogleMeetRealtimeStrategy,
) -> GoogleMeetRealtimeStrategy:
    normalized = normalize_optional_lowercase_string(value)
    if normalized in {"agent", "bidi"}:
        return normalized
    return fallback


def _resolve_chrome_audio_format(value: Any) -> GoogleMeetChromeAudioFormat | None:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return None
    lowered = normalized.lower().replace("_", "-")
    if lowered in {"pcm16-24khz", "pcm16-24k", "pcm24", "pcm"}:
        return "pcm16-24khz"
    if lowered in {"g711-ulaw-8khz", "g711-ulaw-8k", "g711-ulaw", "mulaw", "mu-law"}:
        return "g711-ulaw-8khz"
    return None


def _resolve_audio_buffer_bytes(value: Any, fallback: float) -> int:
    number = _resolve_number(value, fallback)
    if not (number > 0 and number == number):
        return int(fallback)
    return max(SOX_MIN_BUFFER_BYTES, int(number))


def _default_audio_input_command(
    audio_format: GoogleMeetChromeAudioFormat,
    buffer_bytes: int,
) -> list[str]:
    base = (
        LEGACY_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE
        if audio_format == "g711-ulaw-8khz"
        else DEFAULT_GOOGLE_MEET_AUDIO_INPUT_COMMAND_BASE
    )
    return _with_sox_buffer(list(base), buffer_bytes)


def _default_audio_output_command(
    audio_format: GoogleMeetChromeAudioFormat,
    buffer_bytes: int,
) -> list[str]:
    base = (
        LEGACY_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE
        if audio_format == "g711-ulaw-8khz"
        else DEFAULT_GOOGLE_MEET_AUDIO_OUTPUT_COMMAND_BASE
    )
    return _with_sox_buffer(list(base), buffer_bytes)


def resolve_google_meet_config(input_value: Any) -> GoogleMeetConfig:
    return resolve_google_meet_config_with_env(input_value)


def resolve_google_meet_config_with_env(
    input_value: Any,
    env: dict[str, str] | None = None,
) -> GoogleMeetConfig:
    env_map = env if env is not None else dict(os.environ)
    raw = as_record(input_value)
    defaults = as_record(raw.get("defaults"))
    preview = as_record(raw.get("preview"))
    chrome = as_record(raw.get("chrome"))
    configured_audio_input_command = _resolve_string_array(chrome.get("audioInputCommand"))
    configured_audio_output_command = _resolve_string_array(chrome.get("audioOutputCommand"))
    has_custom_audio_command = (
        configured_audio_input_command is not None or configured_audio_output_command is not None
    )
    audio_format = _resolve_chrome_audio_format(chrome.get("audioFormat"))
    if audio_format is None:
        audio_format = (
            "g711-ulaw-8khz" if has_custom_audio_command else DEFAULT_GOOGLE_MEET_CHROME_AUDIO_FORMAT
        )
    audio_buffer_bytes = _resolve_audio_buffer_bytes(
        chrome.get("audioBufferBytes"),
        DEFAULT_GOOGLE_MEET_AUDIO_BUFFER_BYTES,
    )
    chrome_node = as_record(raw.get("chromeNode"))
    twilio = as_record(raw.get("twilio"))
    voice_call = as_record(raw.get("voiceCall"))
    realtime = as_record(raw.get("realtime"))
    realtime_provider = normalize_optional_string(realtime.get("provider"))
    resolved_realtime_provider = realtime_provider or "openai"
    oauth = as_record(raw.get("oauth"))
    auth = as_record(raw.get("auth"))

    transcription_provider = normalize_optional_string(realtime.get("transcriptionProvider"))
    if transcription_provider is None:
        if realtime_provider and realtime_provider != "google":
            transcription_provider = resolved_realtime_provider
        else:
            transcription_provider = "openai"

    intro_message = _normalize_string_allow_empty(realtime.get("introMessage"))
    if intro_message is None:
        intro_message = DEFAULT_GOOGLE_MEET_REALTIME_INTRO_MESSAGE

    return GoogleMeetConfig(
        enabled=_resolve_boolean(raw.get("enabled"), True),
        defaults=GoogleMeetDefaultsConfig(
            meeting=normalize_optional_string(defaults.get("meeting"))
            or _read_env_string(env_map, GOOGLE_MEET_DEFAULT_MEETING_KEYS),
        ),
        preview=GoogleMeetPreviewConfig(
            enrollment_acknowledged=_resolve_boolean(
                preview.get("enrollmentAcknowledged"),
                _read_env_boolean(env_map, GOOGLE_MEET_PREVIEW_ACK_KEYS) or False,
            ),
        ),
        default_transport=_resolve_transport(raw.get("defaultTransport"), "chrome"),
        default_mode=_resolve_mode(raw.get("defaultMode"), "agent"),
        chrome=GoogleMeetChromeConfig(
            audio_backend="blackhole-2ch",
            audio_format=audio_format,
            audio_buffer_bytes=audio_buffer_bytes,
            launch=_resolve_boolean(chrome.get("launch"), True),
            browser_profile=normalize_optional_string(chrome.get("browserProfile")),
            guest_name=normalize_optional_string(chrome.get("guestName")) or "OpenClaw Agent",
            reuse_existing_tab=_resolve_boolean(chrome.get("reuseExistingTab"), True),
            auto_join=_resolve_boolean(chrome.get("autoJoin"), True),
            join_timeout_ms=_resolve_timer_config_ms(chrome.get("joinTimeoutMs"), 30_000),
            wait_for_in_call_ms=_resolve_timer_config_ms(chrome.get("waitForInCallMs"), 20_000),
            audio_input_command=configured_audio_input_command
            or _default_audio_input_command(audio_format, audio_buffer_bytes),
            audio_output_command=configured_audio_output_command
            or _default_audio_output_command(audio_format, audio_buffer_bytes),
            barge_in_input_command=_resolve_string_array(chrome.get("bargeInInputCommand")),
            barge_in_rms_threshold=int(
                _resolve_number(
                    chrome.get("bargeInRmsThreshold"),
                    DEFAULT_GOOGLE_MEET_BARGE_IN_RMS_THRESHOLD,
                )
            ),
            barge_in_peak_threshold=int(
                _resolve_number(
                    chrome.get("bargeInPeakThreshold"),
                    DEFAULT_GOOGLE_MEET_BARGE_IN_PEAK_THRESHOLD,
                )
            ),
            barge_in_cooldown_ms=_resolve_timer_config_ms(
                chrome.get("bargeInCooldownMs"),
                DEFAULT_GOOGLE_MEET_BARGE_IN_COOLDOWN_MS,
            ),
            audio_bridge_command=_resolve_string_array(chrome.get("audioBridgeCommand")),
            audio_bridge_health_command=_resolve_string_array(chrome.get("audioBridgeHealthCommand")),
        ),
        chrome_node=GoogleMeetChromeNodeConfig(
            node=normalize_optional_string(chrome_node.get("node")),
        ),
        twilio=GoogleMeetTwilioConfig(
            default_dial_in_number=normalize_optional_string(twilio.get("defaultDialInNumber")),
            default_pin=normalize_optional_string(twilio.get("defaultPin")),
            default_dtmf_sequence=normalize_optional_string(twilio.get("defaultDtmfSequence")),
        ),
        voice_call=GoogleMeetVoiceCallConfig(
            enabled=_resolve_boolean(voice_call.get("enabled"), True),
            gateway_url=normalize_optional_string(voice_call.get("gatewayUrl")),
            token=normalize_optional_string(voice_call.get("token")),
            request_timeout_ms=_resolve_timer_config_ms(voice_call.get("requestTimeoutMs"), 30_000),
            dtmf_delay_ms=_resolve_timer_config_ms(voice_call.get("dtmfDelayMs"), 12_000),
            post_dtmf_speech_delay_ms=_resolve_timer_config_ms(
                voice_call.get("postDtmfSpeechDelayMs"),
                5_000,
            ),
            intro_message=normalize_optional_string(voice_call.get("introMessage")),
        ),
        realtime=GoogleMeetRealtimeConfig(
            strategy=_resolve_realtime_strategy(realtime.get("strategy"), "agent"),
            provider=resolved_realtime_provider,
            transcription_provider=transcription_provider,
            voice_provider=normalize_optional_string(realtime.get("voiceProvider")),
            model=normalize_optional_string(realtime.get("model")),
            instructions=normalize_optional_string(realtime.get("instructions"))
            or DEFAULT_GOOGLE_MEET_REALTIME_INSTRUCTIONS,
            intro_message=intro_message,
            agent_id=normalize_optional_string(realtime.get("agentId")),
            tool_policy=resolve_realtime_voice_agent_consult_tool_policy(
                realtime.get("toolPolicy"),
                "safe-read-only",
            ),
            providers=_resolve_providers_config(realtime.get("providers")),
        ),
        oauth=GoogleMeetOAuthConfig(
            client_id=normalize_optional_string(oauth.get("clientId"))
            or normalize_optional_string(auth.get("clientId"))
            or _read_env_string(env_map, GOOGLE_MEET_CLIENT_ID_KEYS),
            client_secret=normalize_optional_string(oauth.get("clientSecret"))
            or normalize_optional_string(auth.get("clientSecret"))
            or _read_env_string(env_map, GOOGLE_MEET_CLIENT_SECRET_KEYS),
            refresh_token=normalize_optional_string(oauth.get("refreshToken"))
            or _read_env_string(env_map, GOOGLE_MEET_REFRESH_TOKEN_KEYS),
            access_token=normalize_optional_string(oauth.get("accessToken"))
            or _read_env_string(env_map, GOOGLE_MEET_ACCESS_TOKEN_KEYS),
            expires_at=_resolve_optional_number(oauth.get("expiresAt"))
            or _read_env_number(env_map, GOOGLE_MEET_ACCESS_TOKEN_EXPIRES_AT_KEYS),
        ),
        auth=GoogleMeetAuthConfig(
            provider="google-oauth",
            client_id=normalize_optional_string(auth.get("clientId")),
            client_secret=normalize_optional_string(auth.get("clientSecret")),
            token_path=normalize_optional_string(auth.get("tokenPath")),
        ),
    )
