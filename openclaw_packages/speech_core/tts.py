from __future__ import annotations

import json
import math
import os
import re
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, TypedDict, Union

from openclaw.plugin_sdk.channel_targets import resolve_channel_tts_voice_delivery
from openclaw.plugin_sdk.error_runtime import format_error_message
from openclaw.plugin_sdk.logging_core import redact_sensitive_text
from openclaw.plugin_sdk.media_runtime import transcode_audio_buffer
from openclaw.plugin_sdk.number_runtime import clamp_timer_timeout_ms
from openclaw.plugin_sdk.reply_payload import (
    mark_reply_payload_as_tts_supplement,
    resolve_sendable_outbound_reply_parts,
)
from openclaw.plugin_sdk.runtime_config_snapshot import (
    get_runtime_config_snapshot,
    get_runtime_config_source_snapshot,
    select_applicable_runtime_config,
)
from openclaw.plugin_sdk.runtime_env import is_verbose, log_verbose
from openclaw.plugin_sdk.sandbox import temp_workspace_sync, resolve_preferred_openclaw_tmp_dir
from openclaw.plugin_sdk.security_runtime import private_file_store_sync
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw.plugin_sdk.text_chunking import strip_markdown
from openclaw.plugin_sdk.text_utility_runtime import resolve_config_dir, resolve_user_path

from .api import (
    canonicalize_speech_provider_id,
    get_speech_provider,
    list_speech_providers,
    normalize_speech_provider_id,
    normalize_tts_auto_mode,
    parse_tts_directives,
    resolve_effective_tts_config,
    schedule_cleanup,
    summarize_text,
)
from .speaker import with_speaker_selection_compat
from .voice_models import (
    resolve_primary_voice_provider_candidate,
    resolve_supported_voice_model_refs,
    resolve_voice_model_refs,
    resolve_voice_provider_candidates,
    voice_provider_supports_model,
)

if TYPE_CHECKING:
    from openclaw.plugin_sdk.config_contracts import (
        OpenClawConfig,
        ResolvedTtsPersona,
        TtsAutoMode,
        TtsConfig,
        TtsModelOverrideConfig,
        TtsProvider,
    )
    from openclaw.plugin_sdk.reply_payload import ReplyPayload
    from .api import (
        ResolvedTtsConfig,
        ResolvedTtsModelOverrides,
        SpeechProviderConfig,
        SpeechProviderOverrides,
        SpeechProviderPlugin,
        SpeechVoiceOption,
        TtsDirectiveOverrides,
        TtsDirectiveParseResult,
    )
    from .voice_models import VoiceModelRef, VoiceModelProvider, VoiceProviderCandidate


DEFAULT_TIMEOUT_MS = 30000
DEFAULT_TTS_MAX_LENGTH = 1500
DEFAULT_TTS_SUMMARIZE = True
DEFAULT_MAX_TEXT_LENGTH = 4096


class TtsUserPrefs(TypedDict, total=False):
    tts: Dict[str, Any]


TtsAttemptReasonCode = Literal[
    "success",
    "no_provider_registered",
    "not_configured",
    "unsupported_for_streaming",
    "unsupported_for_telephony",
    "timeout",
    "provider_error",
]


class TtsProviderAttempt(TypedDict, total=False):
    provider: str
    outcome: Literal["success", "skipped", "failed"]
    reasonCode: TtsAttemptReasonCode
    persona: Optional[str]
    personaBinding: Optional[Literal["applied", "missing", "none"]]
    latencyMs: Optional[int]
    error: Optional[str]


class TtsResult(TypedDict, total=False):
    success: bool
    audioPath: Optional[str]
    error: Optional[str]
    latencyMs: Optional[int]
    provider: Optional[str]
    persona: Optional[str]
    fallbackFrom: Optional[str]
    attemptedProviders: Optional[List[str]]
    attempts: Optional[List[TtsProviderAttempt]]
    outputFormat: Optional[str]
    voiceCompatible: Optional[bool]
    audioAsVoice: Optional[bool]
    target: Optional[Literal["audio-file", "voice-note"]]


class TtsSynthesisResult(TypedDict, total=False):
    success: bool
    audioBuffer: Optional[bytes]
    error: Optional[str]
    latencyMs: Optional[int]
    provider: Optional[str]
    providerModel: Optional[str]
    providerVoice: Optional[str]
    persona: Optional[str]
    fallbackFrom: Optional[str]
    attemptedProviders: Optional[List[str]]
    attempts: Optional[List[TtsProviderAttempt]]
    outputFormat: Optional[str]
    voiceCompatible: Optional[bool]
    fileExtension: Optional[str]
    target: Optional[Literal["audio-file", "voice-note"]]


class TtsStreamResult(TypedDict, total=False):
    success: bool
    audioStream: Optional[Any]
    error: Optional[str]
    latencyMs: Optional[int]
    provider: Optional[str]
    providerModel: Optional[str]
    providerVoice: Optional[str]
    persona: Optional[str]
    fallbackFrom: Optional[str]
    attemptedProviders: Optional[List[str]]
    attempts: Optional[List[TtsProviderAttempt]]
    outputFormat: Optional[str]
    voiceCompatible: Optional[bool]
    fileExtension: Optional[str]
    target: Optional[Literal["audio-file", "voice-note"]]
    release: Optional[Callable]


TtsSynthesisStreamResult = TtsStreamResult


class TtsTelephonyResult(TypedDict, total=False):
    success: bool
    audioBuffer: Optional[bytes]
    error: Optional[str]
    latencyMs: Optional[int]
    provider: Optional[str]
    providerModel: Optional[str]
    providerVoice: Optional[str]
    persona: Optional[str]
    fallbackFrom: Optional[str]
    attemptedProviders: Optional[List[str]]
    attempts: Optional[List[TtsProviderAttempt]]
    outputFormat: Optional[str]
    sampleRate: Optional[int]


class TtsStatusEntry(TypedDict, total=False):
    timestamp: int
    success: bool
    textLength: int
    summarized: bool
    provider: Optional[str]
    persona: Optional[str]
    fallbackFrom: Optional[str]
    attemptedProviders: Optional[List[str]]
    attempts: Optional[List[TtsProviderAttempt]]
    latencyMs: Optional[int]
    error: Optional[str]


_last_tts_attempt: Optional[TtsStatusEntry] = None


def _resolve_positive_timeout_ms(timeout_ms):
    if isinstance(timeout_ms, (int, float)) and timeout_ms == timeout_ms and timeout_ms > 0:
        return clamp_timer_timeout_ms(timeout_ms)
    return None


def _resolve_speech_provider_timeout_ms(config, provider, timeout_ms=None):
    if timeout_ms is not None:
        return _resolve_positive_timeout_ms(timeout_ms) or config["timeoutMs"]
    if config.get("timeoutMsSource") != "default":
        return _resolve_positive_timeout_ms(config["timeoutMs"]) or DEFAULT_TIMEOUT_MS
    return _resolve_positive_timeout_ms(provider.get("defaultTimeoutMs")) or config["timeoutMs"]


def _resolve_configured_tts_auto_mode(raw):
    return normalize_tts_auto_mode(raw.get("auto")) or ("always" if raw.get("enabled") else "off")


def _normalize_configured_speech_provider_id(provider_id):
    normalized = normalize_speech_provider_id(provider_id)
    if not normalized:
        return None
    return "microsoft" if normalized == "edge" else normalized


def _normalize_tts_persona_id(persona_id):
    return normalize_optional_lowercase_string(persona_id)


def _resolve_tts_prefs_path_value(prefs_path):
    if prefs_path and prefs_path.strip():
        return resolve_user_path(prefs_path.strip())
    env_path_raw = os.environ.get("OPENCLAW_TTS_PREFS")
    env_path = env_path_raw.strip() if env_path_raw else ""
    if env_path:
        return resolve_user_path(env_path)
    return os.path.join(resolve_config_dir(os.environ), "settings", "tts.json")


def _resolve_model_override_policy(overrides=None):
    enabled = overrides.get("enabled", True) if overrides else True
    if not enabled:
        return {
            "enabled": False, "allowText": False, "allowProvider": False,
            "allowVoice": False, "allowModelId": False, "allowVoiceSettings": False,
            "allowNormalization": False, "allowSeed": False,
        }

    def allow(value, default=True):
        return value if value is not None else default

    o = overrides or {}
    return {
        "enabled": True,
        "allowText": allow(o.get("allowText")),
        "allowProvider": allow(o.get("allowProvider"), False),
        "allowVoice": allow(o.get("allowVoice")),
        "allowModelId": allow(o.get("allowModelId")),
        "allowVoiceSettings": allow(o.get("allowVoiceSettings")),
        "allowNormalization": allow(o.get("allowNormalization")),
        "allowSeed": allow(o.get("allowSeed")),
    }


def _sort_speech_providers_for_auto_selection(cfg=None):
    providers = list_speech_providers(cfg)

    def sort_key(provider):
        order = provider.get("autoSelectOrder", float("inf"))
        return (order, provider.get("id", ""))

    return sorted(providers, key=sort_key)


def _resolve_tts_runtime_config(cfg):
    result = select_applicable_runtime_config(
        inputConfig=cfg,
        runtimeConfig=get_runtime_config_snapshot(),
        runtimeSourceConfig=get_runtime_config_source_snapshot(),
    )
    return result if result is not None else cfg


def _as_provider_config(value):
    if isinstance(value, dict) and not isinstance(value, list):
        return value
    return {}


def _as_provider_config_map(value):
    if isinstance(value, dict) and not isinstance(value, list):
        return value
    return {}


def _has_own_property(value, key):
    return isinstance(value, dict) and key in value


def _normalize_provider_config_map(value):
    raw_map = _as_provider_config_map(value)
    if len(raw_map) == 0:
        return None
    next_map = {}
    for provider_id, provider_config in raw_map.items():
        normalized = _normalize_configured_speech_provider_id(provider_id) or provider_id
        next_map[normalized] = with_speaker_selection_compat(_as_provider_config(provider_config))
    return next_map


def _collect_tts_personas(raw):
    raw_personas = _as_provider_config_map(raw.get("personas"))
    personas = {}
    for id_val, value in raw_personas.items():
        normalized_id = _normalize_tts_persona_id(id_val)
        if not normalized_id or not isinstance(value, dict) or isinstance(value, list):
            continue
        persona = dict(value)
        persona["id"] = normalized_id
        persona["provider"] = _normalize_configured_speech_provider_id(persona.get("provider")) or persona.get("provider")
        persona["providers"] = _normalize_provider_config_map(persona.get("providers"))
        personas[normalized_id] = persona
    return personas


def _resolve_persona_provider_config(persona, provider_id):
    if not persona or not persona.get("providers"):
        return None
    normalized = _normalize_configured_speech_provider_id(provider_id) or provider_id
    if _has_own_property(persona["providers"], normalized):
        return persona["providers"][normalized]
    if _has_own_property(persona["providers"], provider_id):
        return persona["providers"][provider_id]
    return None


def _merge_provider_config_with_persona(provider_config, persona, provider_id):
    if not persona:
        return {"providerConfig": provider_config, "personaBinding": "none"}
    persona_provider_config = _resolve_persona_provider_config(persona, provider_id)
    if not persona_provider_config:
        return {"providerConfig": provider_config, "personaBinding": "missing"}
    return {
        "providerConfig": {**provider_config, **persona_provider_config},
        "personaProviderConfig": persona_provider_config,
        "personaBinding": "applied",
    }


def _resolve_raw_provider_config(raw, provider_id):
    if not raw:
        return {}
    raw_providers = _as_provider_config_map(raw.get("providers"))
    direct = raw_providers.get(provider_id) or raw.get(provider_id)
    return with_speaker_selection_compat(_as_provider_config(direct))


def _resolve_configured_speech_voice_model_refs(cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else None
    voice_model = None
    if effective_cfg:
        voice_model = effective_cfg.get("agents", {}).get("defaults", {}).get("voiceModel")
    return resolve_supported_voice_model_refs(
        config=voice_model,
        providers=_sort_speech_providers_for_auto_selection(effective_cfg),
    )


def _resolve_configured_speech_voice_model_for_provider(cfg, provider_id, provider=None, voice_model=None):
    provider = provider or get_speech_provider(provider_id, cfg)
    if voice_model:
        return voice_model if voice_provider_supports_model(provider, voice_model["model"]) else None
    vm = None
    if cfg:
        vm = cfg.get("agents", {}).get("defaults", {}).get("voiceModel")
    refs = resolve_supported_voice_model_refs(
        config=vm,
        providers=[provider] if provider else [],
        providerId=provider_id,
    )
    return refs[0] if refs else None


def _apply_voice_model_to_speech_provider_config(cfg, provider_id, provider_config, provider=None, voice_model=None):
    resolved_voice_model = _resolve_configured_speech_voice_model_for_provider(
        cfg=cfg, provider_id=provider_id, provider=provider, voice_model=voice_model,
    )
    if not resolved_voice_model:
        return provider_config
    has_explicit_model = (
        normalize_optional_string(provider_config.get("model"))
        or normalize_optional_string(provider_config.get("modelId"))
    )
    if has_explicit_model:
        return provider_config
    return {**provider_config, "model": resolved_voice_model["model"], "modelId": resolved_voice_model["model"]}


def _resolve_lazy_provider_config(config, provider_id, cfg=None, voice_model=None):
    canonical = _normalize_configured_speech_provider_id(provider_id) or normalize_lowercase_string_or_empty(provider_id)
    existing = None if voice_model else config["providerConfigs"].get(canonical)
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else config["sourceConfig"]
    if existing and not effective_cfg:
        return existing
    raw_config = _resolve_raw_provider_config(config["rawConfig"], canonical)
    raw_base_config = config["rawConfig"]
    raw_providers = _as_provider_config_map(raw_base_config.get("providers") if raw_base_config else None)
    resolved_provider = get_speech_provider(canonical, effective_cfg)
    has_raw_provider_config = (
        canonical in raw_providers
        or (raw_base_config is not None and canonical in raw_base_config)
    )
    raw_provider_config = raw_providers.get(canonical) or (raw_base_config.get(canonical) if raw_base_config else None)
    if not has_raw_provider_config and resolved_provider:
        for alias in (resolved_provider.get("aliases") or []):
            normalized_alias = normalize_speech_provider_id(alias)
            if not normalized_alias:
                continue
            if normalized_alias in raw_providers:
                has_raw_provider_config = True
                raw_provider_config = raw_providers[normalized_alias]
                break
            if raw_base_config and normalized_alias in raw_base_config:
                has_raw_provider_config = True
                raw_provider_config = raw_base_config[normalized_alias]
                break
    compat_raw_provider_config = _apply_voice_model_to_speech_provider_config(
        cfg=effective_cfg, provider_id=canonical,
        provider_config=with_speaker_selection_compat(_as_provider_config(raw_provider_config)),
        provider=resolved_provider, voice_model=voice_model,
    )
    should_inject = has_raw_provider_config or bool(voice_model) or len(raw_providers) == 0
    raw_config_for_provider = dict(raw_base_config) if raw_base_config else {}
    if should_inject:
        raw_providers_copy = dict(raw_providers)
        raw_providers_copy[canonical] = compat_raw_provider_config
        raw_config_for_provider["providers"] = raw_providers_copy
        raw_config_for_provider[canonical] = compat_raw_provider_config
    else:
        raw_config_for_provider["providers"] = raw_providers
    resolve_config_fn = resolved_provider.get("resolveConfig") if resolved_provider else None
    if effective_cfg and resolve_config_fn:
        next_config = resolve_config_fn(
            cfg=effective_cfg, rawConfig=raw_config_for_provider,
            timeoutMs=_resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider),
        )
    else:
        next_config = _apply_voice_model_to_speech_provider_config(
            cfg=effective_cfg, provider_id=canonical, provider_config=raw_config,
            provider=resolved_provider, voice_model=voice_model,
        )
    next_config = with_speaker_selection_compat(next_config)
    if not voice_model:
        config["providerConfigs"][canonical] = next_config
    return next_config


def _collect_direct_provider_config_entries(raw):
    entries = {}
    raw_providers = _as_provider_config_map(raw.get("providers"))
    for provider_id, value in raw_providers.items():
        normalized = _normalize_configured_speech_provider_id(provider_id) or provider_id
        entries[normalized] = with_speaker_selection_compat(_as_provider_config(value))
    reserved_keys = {
        "auto", "enabled", "maxTextLength", "mode", "modelOverrides",
        "persona", "personas", "prefsPath", "provider", "providers",
        "summaryModel", "timeoutMs",
    }
    for key, value in raw.items():
        if key in reserved_keys:
            continue
        if not isinstance(value, dict) or isinstance(value, list):
            continue
        normalized = _normalize_configured_speech_provider_id(key) or key
        if normalized not in entries:
            entries[normalized] = with_speaker_selection_compat(_as_provider_config(value))
    return entries


def get_resolved_speech_provider_config(config, provider_id, cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else config["sourceConfig"]
    canonical = (
        canonicalize_speech_provider_id(provider_id, effective_cfg)
        or _normalize_configured_speech_provider_id(provider_id)
        or normalize_lowercase_string_or_empty(provider_id)
    )
    return _resolve_lazy_provider_config(config, canonical, effective_cfg)


def _get_resolved_speech_provider_config_for_voice_model(config, provider_id, cfg, voice_model=None):
    if not voice_model:
        return get_resolved_speech_provider_config(config, provider_id, cfg)
    effective_cfg = _resolve_tts_runtime_config(cfg)
    canonical = (
        canonicalize_speech_provider_id(provider_id, effective_cfg)
        or _normalize_configured_speech_provider_id(provider_id)
        or normalize_lowercase_string_or_empty(provider_id)
    )
    return _resolve_lazy_provider_config(config, canonical, effective_cfg, voice_model)


def resolve_tts_config(cfg_input, context_or_agent_id=None):
    cfg = _resolve_tts_runtime_config(cfg_input)
    raw = resolve_effective_tts_config(cfg, context_or_agent_id)
    provider_source = "config" if raw.get("provider") else "default"
    timeout_ms = raw.get("timeoutMs", DEFAULT_TIMEOUT_MS)
    timeout_ms_source = "default" if raw.get("timeoutMs") is None else "config"
    auto = _resolve_configured_tts_auto_mode(raw)
    persona = _normalize_tts_persona_id(raw.get("persona"))
    return {
        "auto": auto,
        "mode": raw.get("mode") or "final",
        "provider": (
            _normalize_configured_speech_provider_id(raw.get("provider"))
            or (normalize_optional_lowercase_string(raw.get("provider")) if provider_source == "config" else "")
        ),
        "providerSource": provider_source,
        "persona": persona,
        "personas": _collect_tts_personas(raw),
        "summaryModel": normalize_optional_string(raw.get("summaryModel")),
        "modelOverrides": _resolve_model_override_policy(raw.get("modelOverrides")),
        "providerConfigs": _collect_direct_provider_config_entries(raw),
        "prefsPath": raw.get("prefsPath"),
        "maxTextLength": raw.get("maxTextLength", DEFAULT_MAX_TEXT_LENGTH),
        "timeoutMs": timeout_ms,
        "timeoutMsSource": timeout_ms_source,
        "rawConfig": raw,
        "sourceConfig": cfg,
    }


def resolve_tts_prefs_path(config):
    return _resolve_tts_prefs_path_value(config["prefsPath"])


def _resolve_tts_auto_mode_from_prefs(prefs):
    auto = normalize_tts_auto_mode((prefs.get("tts") or {}).get("auto"))
    if auto:
        return auto
    tts = prefs.get("tts")
    if isinstance(tts, dict) and isinstance(tts.get("enabled"), bool):
        return "always" if tts["enabled"] else "off"
    return None


def resolve_tts_auto_mode(config, prefs_path, session_auto=None):
    session = normalize_tts_auto_mode(session_auto)
    if session:
        return session
    prefs_auto = _resolve_tts_auto_mode_from_prefs(_read_prefs(prefs_path))
    if prefs_auto:
        return prefs_auto
    return config["auto"]


def _resolve_effective_tts_auto_state(cfg, session_auto=None, agent_id=None, channel_id=None, account_id=None):
    raw = resolve_effective_tts_config(cfg, {
        "agentId": agent_id, "channelId": channel_id, "accountId": account_id,
    })
    prefs_path = _resolve_tts_prefs_path_value(raw.get("prefsPath"))
    session = normalize_tts_auto_mode(session_auto)
    if session:
        return {"autoMode": session, "prefsPath": prefs_path}
    prefs_auto = _resolve_tts_auto_mode_from_prefs(_read_prefs(prefs_path))
    if prefs_auto:
        return {"autoMode": prefs_auto, "prefsPath": prefs_path}
    return {"autoMode": _resolve_configured_tts_auto_mode(raw), "prefsPath": prefs_path}


def _read_prefs(prefs_path):
    try:
        if not os.path.exists(prefs_path):
            return {}
        with open(prefs_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _atomic_write_file_sync(file_path, content):
    private_file_store_sync(os.path.dirname(file_path)).write_text(os.path.basename(file_path), content)


def _update_prefs(prefs_path, update):
    prefs = _read_prefs(prefs_path)
    update(prefs)
    _atomic_write_file_sync(prefs_path, json.dumps(prefs, indent=2))


def is_tts_enabled(config, prefs_path, session_auto=None):
    return resolve_tts_auto_mode(config, prefs_path, session_auto) != "off"


def set_tts_auto_mode(prefs_path, mode):
    def update(prefs):
        next_tts = dict(prefs.get("tts") or {})
        next_tts.pop("enabled", None)
        next_tts["auto"] = mode
        prefs["tts"] = next_tts
    _update_prefs(prefs_path, update)


def set_tts_enabled(prefs_path, enabled):
    set_tts_auto_mode(prefs_path, "always" if enabled else "off")


def _resolve_tts_persona_from_prefs(config, prefs):
    tts = prefs.get("tts")
    if isinstance(tts, dict) and "persona" in tts:
        prefs_persona = _normalize_tts_persona_id(tts.get("persona"))
        return config["personas"].get(prefs_persona) if prefs_persona else None
    config_persona = _normalize_tts_persona_id(config.get("persona"))
    return config["personas"].get(config_persona) if config_persona else None


def get_tts_persona(config, prefs_path):
    return _resolve_tts_persona_from_prefs(config, _read_prefs(prefs_path))


def get_tts_provider(config, prefs_path):
    prefs = _read_prefs(prefs_path)
    tts = prefs.get("tts") or {}
    prefs_provider = (
        canonicalize_speech_provider_id(tts.get("provider"))
        or _normalize_configured_speech_provider_id(tts.get("provider"))
    )
    if prefs_provider:
        return prefs_provider
    active_persona = _resolve_tts_persona_from_prefs(config, prefs)
    persona_provider = (
        canonicalize_speech_provider_id(active_persona.get("provider"), config["sourceConfig"]) if active_persona else None
        or _normalize_configured_speech_provider_id(active_persona.get("provider")) if active_persona else None
    )
    if persona_provider and get_speech_provider(persona_provider, config["sourceConfig"]):
        return persona_provider
    if config["providerSource"] == "config":
        return _normalize_configured_speech_provider_id(config["provider"]) or config["provider"]
    configured_refs = _resolve_configured_speech_voice_model_refs(config["sourceConfig"])
    configured_voice_provider = configured_refs[0]["provider"] if configured_refs else None
    if configured_voice_provider and get_speech_provider(configured_voice_provider, config["sourceConfig"]):
        return configured_voice_provider
    effective_cfg = config["sourceConfig"]
    for provider in _sort_speech_providers_for_auto_selection(effective_cfg):
        is_configured_fn = provider.get("isConfigured")
        if is_configured_fn and is_configured_fn(
            cfg=effective_cfg,
            providerConfig=config["providerConfigs"].get(provider["id"], {}),
            timeoutMs=_resolve_speech_provider_timeout_ms(config=config, provider=provider),
        ):
            return provider["id"]
    return config["provider"]


def list_tts_personas(config):
    return sorted(config["personas"].values(), key=lambda p: p["id"])


def set_tts_persona(prefs_path, persona):
    def update(prefs):
        next_tts = dict(prefs.get("tts") or {})
        normalized = _normalize_tts_persona_id(persona)
        next_tts["persona"] = normalized if normalized else None
        prefs["tts"] = next_tts
    _update_prefs(prefs_path, update)


def set_tts_provider(prefs_path, provider):
    def update(prefs):
        prefs["tts"] = {**prefs.get("tts", {}), "provider": canonicalize_speech_provider_id(provider) or provider}
    _update_prefs(prefs_path, update)


def get_tts_max_length(prefs_path):
    prefs = _read_prefs(prefs_path)
    return (prefs.get("tts") or {}).get("maxLength", DEFAULT_TTS_MAX_LENGTH)


def set_tts_max_length(prefs_path, max_length):
    def update(prefs):
        prefs["tts"] = {**prefs.get("tts", {}), "maxLength": max_length}
    _update_prefs(prefs_path, update)


def is_summarization_enabled(prefs_path):
    prefs = _read_prefs(prefs_path)
    return (prefs.get("tts") or {}).get("summarize", DEFAULT_TTS_SUMMARIZE)


def set_summarization_enabled(prefs_path, enabled):
    def update(prefs):
        prefs["tts"] = {**prefs.get("tts", {}), "summarize": enabled}
    _update_prefs(prefs_path, update)


def get_last_tts_attempt():
    return _last_tts_attempt


def set_last_tts_attempt(entry):
    global _last_tts_attempt
    _last_tts_attempt = entry


def _supports_native_voice_note_tts(channel):
    return resolve_channel_tts_voice_delivery(channel) is not None


def _supports_transcoded_voice_note_tts(channel):
    delivery = resolve_channel_tts_voice_delivery(channel)
    if not delivery:
        return False
    return delivery.get("synthesisTarget") == "voice-note" and delivery.get("transcodesAudio") is True


def _resolve_tts_synthesis_target(channel):
    delivery = resolve_channel_tts_voice_delivery(channel)
    return (delivery or {}).get("synthesisTarget") or "audio-file"


def _supports_audio_file_voice_memo_output(file_extension=None, output_format=None, audio_file_formats=None):
    formats = set()
    if audio_file_formats:
        for f in audio_file_formats:
            formats.add(f.strip().lower())
    if len(formats) == 0:
        return False
    ext = file_extension.strip().lower() if file_extension else None
    if ext and ext.replace(".", "", 1) if ext.startswith(".") else ext in formats:
        return True
    fmt = output_format.strip().lower() if output_format else None
    return fmt in formats if fmt else False


def _should_deliver_tts_as_voice(channel, target, voice_compatible, file_extension=None, output_format=None):
    delivery = resolve_channel_tts_voice_delivery(channel)
    if not delivery:
        return False
    if delivery.get("synthesisTarget") == "audio-file":
        return (
            target == "audio-file"
            and _supports_audio_file_voice_memo_output(
                fileExtension=file_extension,
                outputFormat=output_format,
                audioFileFormats=delivery.get("audioFileFormats"),
            )
        )
    if target != "voice-note":
        return False
    return voice_compatible is True or delivery.get("transcodesAudio") is True


def resolve_tts_provider_order(primary, cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else None
    normalized_primary = canonicalize_speech_provider_id(primary, effective_cfg) or primary
    ordered = []
    seen = set()

    def add(provider):
        if provider not in seen:
            seen.add(provider)
            ordered.append(provider)

    add(normalized_primary)
    vm = None
    if effective_cfg:
        vm = effective_cfg.get("agents", {}).get("defaults", {}).get("voiceModel")
    for ref in resolve_voice_model_refs(vm):
        provider = canonicalize_speech_provider_id(ref["provider"], effective_cfg) or ref["provider"]
        if provider != normalized_primary:
            add(provider)
    for provider in _sort_speech_providers_for_auto_selection(effective_cfg):
        normalized = provider["id"]
        if normalized != normalized_primary:
            add(normalized)
    return ordered


def _resolve_tts_provider_candidates(primary, cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else None
    normalized_primary = canonicalize_speech_provider_id(primary, effective_cfg) or primary
    vm = None
    if effective_cfg:
        vm = effective_cfg.get("agents", {}).get("defaults", {}).get("voiceModel")
    return resolve_voice_provider_candidates(
        primaryProvider=normalized_primary,
        providers=_sort_speech_providers_for_auto_selection(effective_cfg),
        voiceModelConfig=vm,
    )


def _resolve_primary_tts_provider_candidate(primary, cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else None
    vm = None
    if effective_cfg:
        vm = effective_cfg.get("agents", {}).get("defaults", {}).get("voiceModel")
    return resolve_primary_voice_provider_candidate(
        primaryProvider=canonicalize_speech_provider_id(primary, effective_cfg) or primary,
        providers=_sort_speech_providers_for_auto_selection(effective_cfg),
        voiceModelConfig=vm,
    )


def is_tts_provider_configured(config, provider, cfg=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else config["sourceConfig"]
    resolved_provider = get_speech_provider(provider, effective_cfg)
    if not resolved_provider:
        return False
    is_configured_fn = resolved_provider.get("isConfigured")
    if not is_configured_fn:
        return False
    return bool(is_configured_fn(
        cfg=effective_cfg,
        providerConfig=get_resolved_speech_provider_config(config, resolved_provider["id"], effective_cfg),
        timeoutMs=_resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider),
    ))


def _format_tts_provider_error(provider, err):
    if isinstance(err, Exception):
        error = err
    else:
        error = Exception(str(err))
    if type(error).__name__ == "AbortError":
        return f"{provider}: request timed out"
    return f"{provider}: {redact_sensitive_text(str(error))}"


def _sanitize_tts_error_for_log(err):
    raw = format_error_message(err)
    return redact_sensitive_text(raw).replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def _build_tts_failure_result(errors, attempted_providers=None, attempts=None, persona=None):
    return {
        "success": False,
        "error": f"TTS conversion failed: {'; '.join(errors) or 'no providers available'}",
        "attemptedProviders": attempted_providers,
        "attempts": attempts,
        "persona": persona,
    }


def _resolve_ready_speech_provider(provider, cfg, config, persona=None, voice_model=None, require_telephony=False):
    resolved_provider = get_speech_provider(provider, cfg)
    if not resolved_provider:
        return {"kind": "skip", "reasonCode": "no_provider_registered", "message": f"{provider}: no provider registered"}
    provider_config = _get_resolved_speech_provider_config_for_voice_model(
        config=config, provider_id=resolved_provider["id"], cfg=cfg, voice_model=voice_model,
    )
    merged = _merge_provider_config_with_persona(provider_config, persona, resolved_provider["id"])
    if persona and persona.get("fallbackPolicy") == "fail" and merged["personaBinding"] == "missing":
        return {"kind": "skip", "reasonCode": "not_configured", "message": f"{provider}: persona {persona['id']} has no provider binding", "personaBinding": "missing"}
    is_configured_fn = resolved_provider.get("isConfigured")
    if is_configured_fn and not is_configured_fn(
        cfg=cfg,
        providerConfig=merged["providerConfig"],
        timeoutMs=_resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider),
    ):
        return {"kind": "skip", "reasonCode": "not_configured", "message": f"{provider}: not configured"}
    if require_telephony and not resolved_provider.get("synthesizeTelephony"):
        return {"kind": "skip", "reasonCode": "unsupported_for_telephony", "message": f"{provider}: unsupported for telephony"}
    synthesis_persona = None
    if persona and persona.get("fallbackPolicy") == "provider-defaults" and merged["personaBinding"] == "missing":
        synthesis_persona = None
    else:
        synthesis_persona = persona
    return {
        "kind": "ready",
        "provider": resolved_provider,
        "providerConfig": merged["providerConfig"],
        "personaProviderConfig": merged.get("personaProviderConfig"),
        "synthesisPersona": synthesis_persona,
        "personaBinding": merged["personaBinding"],
    }


async def _prepare_speech_synthesis(provider, text, cfg, provider_config, provider_overrides=None, persona=None, persona_provider_config=None, target=None, timeout_ms=None):
    prepare_fn = provider.get("prepareSynthesis")
    if not prepare_fn:
        return {"text": text, "providerConfig": provider_config, "providerOverrides": provider_overrides}
    prepared = await prepare_fn(
        text=text, cfg=cfg, providerConfig=provider_config, providerOverrides=provider_overrides,
        persona=persona, personaProviderConfig=persona_provider_config, target=target, timeoutMs=timeout_ms,
    )
    return {
        "text": (prepared or {}).get("text", text),
        "providerConfig": {**provider_config, **(prepared or {}).get("providerConfig", {})} if (prepared or {}).get("providerConfig") else provider_config,
        "providerOverrides": {**provider_overrides, **(prepared or {}).get("providerOverrides", {})} if (prepared or {}).get("providerOverrides") and provider_overrides else ((prepared or {}).get("providerOverrides") if (prepared or {}).get("providerOverrides") else provider_overrides),
    }


def _resolve_tts_request_setup(text, cfg, prefs_path=None, provider_override=None, disable_fallback=False, agent_id=None, channel_id=None, account_id=None):
    cfg = _resolve_tts_runtime_config(cfg)
    config = resolve_tts_config(cfg, {"agentId": agent_id, "channelId": channel_id, "accountId": account_id})
    prefs_path = prefs_path or resolve_tts_prefs_path(config)
    if len(text) > config["maxTextLength"]:
        return {"error": f"Text too long ({len(text)} chars, max {config['maxTextLength']})"}
    user_provider = get_tts_provider(config, prefs_path)
    provider = canonicalize_speech_provider_id(provider_override, cfg) or user_provider
    return {
        "cfg": cfg,
        "config": config,
        "persona": get_tts_persona(config, prefs_path),
        "providers": (
            [_resolve_primary_tts_provider_candidate(provider, cfg)]
            if disable_fallback
            else _resolve_tts_provider_candidates(provider, cfg)
        ),
    }


def _read_tts_result_string(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _resolve_tts_result_model(provider_config, provider_overrides=None):
    po = provider_overrides or {}
    pc = provider_config or {}
    return (
        _read_tts_result_string(po.get("modelId"))
        or _read_tts_result_string(po.get("model"))
        or _read_tts_result_string(pc.get("modelId"))
        or _read_tts_result_string(pc.get("model"))
    )


def _resolve_tts_result_voice(provider_config, provider_overrides=None):
    po = provider_overrides or {}
    pc = provider_config or {}
    return (
        _read_tts_result_string(po.get("speakerVoiceId"))
        or _read_tts_result_string(po.get("speakerVoice"))
        or _read_tts_result_string(po.get("voiceId"))
        or _read_tts_result_string(po.get("voiceName"))
        or _read_tts_result_string(po.get("voice"))
        or _read_tts_result_string(pc.get("speakerVoiceId"))
        or _read_tts_result_string(pc.get("speakerVoice"))
        or _read_tts_result_string(pc.get("voiceId"))
        or _read_tts_result_string(pc.get("voiceName"))
        or _read_tts_result_string(pc.get("voice"))
    )


async def _maybe_pre_transcode_for_voice_delivery(channel, target, audio_buffer, file_extension, output_format=None):
    if target != "audio-file":
        return None
    delivery = resolve_channel_tts_voice_delivery(channel)
    preferred = (delivery or {}).get("preferAudioFileFormat", "").strip().lower() if delivery else ""
    if not preferred:
        return None
    source_ext = file_extension.strip().lower().replace(".", "", 1) if file_extension.startswith(".") else file_extension.strip().lower()
    if source_ext == preferred:
        return None
    outcome = await transcode_audio_buffer(
        audioBuffer=audio_buffer, sourceExtension=source_ext, targetExtension=preferred,
    )
    if not outcome.get("ok"):
        if outcome.get("reason") == "transcoder-failed":
            log_verbose(f"TTS: pre-transcode {source_ext}->{preferred} for channel={channel or '?'} failed: {outcome.get('detail', 'unknown')}")
        return None
    return {"audioBuffer": outcome["buffer"], "fileExtension": f".{preferred}", "outputFormat": preferred}


def _has_legacy_final_media_directive(text):
    return bool(re.search(r"(?:^|\n)\s*MEDIA\s*:", text, re.IGNORECASE))


def build_tts_system_prompt_hint(cfg_input, agent_id=None):
    cfg = _resolve_tts_runtime_config(cfg_input)
    state = _resolve_effective_tts_auto_state(cfg=cfg, agent_id=agent_id)
    auto_mode = state["autoMode"]
    prefs_path = state["prefsPath"]
    if auto_mode == "off":
        return None
    config_for_test = resolve_tts_config(cfg, agent_id)
    persona = get_tts_persona(config_for_test, prefs_path)
    max_length = get_tts_max_length(prefs_path)
    summarize = "on" if is_summarization_enabled(prefs_path) else "off"
    auto_hint = None
    if auto_mode == "inbound":
        auto_hint = "Only use TTS when the user's last message includes audio/voice."
    elif auto_mode == "tagged":
        auto_hint = "Only use TTS when you include [[tts:key=value]] directives or a [[tts:text]]...[[/tts:text]] block."
    lines = ["Voice (TTS) is enabled.", auto_hint]
    if persona:
        label = persona.get("label") or persona["id"]
        desc = persona.get("description")
        lines.append("Active TTS persona: " + label + (f" - {desc}" if desc else "") + ".")
    lines.append("Keep spoken text \u2264" + str(max_length) + " chars to avoid auto-summary (summary " + summarize + ").")
    lines.append("If workspace context (especially MEMORY.md) tells you not to use [[tts:...]] or to use a local/non-tagged voice workflow, follow that workspace instruction instead.")
    lines.append("Use [[tts:...]] and optional [[tts:text]]...[[/tts:text]] to control voice/expressiveness.")
    return "\n".join(line for line in lines if line)


def resolve_explicit_tts_overrides(cfg, prefs_path=None, provider=None, model_id=None, voice_id=None, agent_id=None, channel_id=None, account_id=None):
    cfg = _resolve_tts_runtime_config(cfg)
    provider_input = (provider or "").strip() if provider else ""
    model_id_val = (model_id or "").strip() if model_id else ""
    voice_id_val = (voice_id or "").strip() if voice_id else ""
    config = resolve_tts_config(cfg, {"agentId": agent_id, "channelId": channel_id, "accountId": account_id})
    prefs_path = prefs_path or resolve_tts_prefs_path(config)
    selected_provider = canonicalize_speech_provider_id(provider_input, cfg) or (get_tts_provider(config, prefs_path) if (model_id_val or voice_id_val) else None)
    if provider_input and not selected_provider:
        raise Exception('Unknown TTS provider "' + provider_input + '".')
    if not model_id_val and not voice_id_val:
        return {"provider": selected_provider} if selected_provider else {}
    if not selected_provider:
        raise Exception("TTS model or voice overrides require a resolved provider.")
    provider_obj = get_speech_provider(selected_provider, cfg)
    if not provider_obj:
        raise Exception("speech provider " + selected_provider + " is not registered")
    resolve_talk_overrides_fn = provider_obj.get("resolveTalkOverrides")
    if not resolve_talk_overrides_fn:
        raise Exception('TTS provider "' + selected_provider + '" does not support model or voice overrides.')
    params = {}
    if voice_id_val:
        params["voiceId"] = voice_id_val
    if model_id_val:
        params["modelId"] = model_id_val
    provider_overrides = resolve_talk_overrides_fn(talkProviderConfig={}, params=params)
    if (voice_id_val or model_id_val) and (not provider_overrides or len(provider_overrides) == 0):
        raise Exception('TTS provider "' + selected_provider + '" ignored the requested model or voice overrides.')
    return {"provider": selected_provider, "providerOverrides": {provider_obj["id"]: provider_overrides}}


async def synthesize_speech(text, cfg, prefs_path=None, channel=None, overrides=None, disable_fallback=False, timeout_ms=None, agent_id=None, account_id=None):
    setup = _resolve_tts_request_setup(text=text, cfg=cfg, prefs_path=prefs_path, provider_override=(overrides or {}).get("provider"), disable_fallback=disable_fallback, agent_id=agent_id, channel_id=channel, account_id=account_id)
    if "error" in setup:
        return {"success": False, "error": setup["error"]}
    cfg = setup["cfg"]
    config = setup["config"]
    persona = setup["persona"]
    providers = setup["providers"]
    target = _resolve_tts_synthesis_target(channel)
    errors = []
    attempted_providers = []
    attempts = []
    primary_provider = providers[0]["provider"] if providers else None
    log_verbose("TTS: starting with provider " + str(primary_provider) + ", fallbacks: " + (", ".join(e["provider"] for e in providers[1:]) or "none"))
    for entry in providers:
        provider = entry["provider"]
        voice_model = entry.get("voiceModel")
        attempted_providers.append(provider)
        provider_start = int(time.time() * 1000)
        try:
            resolved_provider = _resolve_ready_speech_provider(provider=provider, cfg=cfg, config=config, persona=persona, voice_model=voice_model)
            if resolved_provider["kind"] == "skip":
                errors.append(resolved_provider["message"])
                attempt = {"provider": provider, "outcome": "skipped", "reasonCode": resolved_provider["reasonCode"], "persona": persona.get("id") if persona else None, "error": resolved_provider["message"]}
                if "personaBinding" in resolved_provider:
                    attempt["personaBinding"] = resolved_provider["personaBinding"]
                attempts.append(attempt)
                log_verbose("TTS: provider " + provider + " skipped (" + resolved_provider["message"] + ")")
                continue
            timeout = _resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider["provider"], timeout_ms=timeout_ms or (voice_model or {}).get("timeoutMs"))
            prepared = await _prepare_speech_synthesis(provider=resolved_provider["provider"], text=text, cfg=cfg, provider_config=resolved_provider["providerConfig"], provider_overrides=(overrides or {}).get("providerOverrides", {}).get(resolved_provider["provider"]["id"]), persona=resolved_provider["synthesisPersona"], persona_provider_config=resolved_provider.get("personaProviderConfig"), target=target, timeout_ms=timeout)
            synthesize_fn = resolved_provider["provider"].get("synthesize")
            synthesis = await synthesize_fn(text=prepared["text"], cfg=cfg, providerConfig=prepared["providerConfig"], target=target, providerOverrides=prepared["providerOverrides"], timeoutMs=timeout)
            latency_ms = int(time.time() * 1000) - provider_start
            attempts.append({"provider": provider, "outcome": "success", "reasonCode": "success", "persona": persona.get("id") if persona else None, "personaBinding": resolved_provider["personaBinding"], "latencyMs": latency_ms})
            return {"success": True, "audioBuffer": synthesis.get("audioBuffer"), "latencyMs": latency_ms, "provider": provider, "providerModel": _resolve_tts_result_model(prepared["providerConfig"], prepared["providerOverrides"]), "providerVoice": _resolve_tts_result_voice(prepared["providerConfig"], prepared["providerOverrides"]), "persona": persona.get("id") if persona else None, "fallbackFrom": primary_provider if provider != primary_provider else None, "attemptedProviders": attempted_providers, "attempts": attempts, "outputFormat": synthesis.get("outputFormat"), "voiceCompatible": synthesis.get("voiceCompatible"), "fileExtension": synthesis.get("fileExtension"), "target": target}
        except Exception as err:
            error_msg = _format_tts_provider_error(provider, err)
            latency_ms = int(time.time() * 1000) - provider_start
            errors.append(error_msg)
            persona_binding = "applied" if _resolve_persona_provider_config(persona, provider) is not None else ("missing" if persona else "none")
            reason_code = "timeout" if type(err).__name__ == "AbortError" else "provider_error"
            attempts.append({"provider": provider, "outcome": "failed", "reasonCode": reason_code, "latencyMs": latency_ms, "persona": persona.get("id") if persona else None, "personaBinding": persona_binding, "error": error_msg})
            raw_error = _sanitize_tts_error_for_log(err)
            if provider == primary_provider:
                has_fallbacks = len(providers) > 1
                log_verbose("TTS: primary provider " + provider + " failed (" + raw_error + ")" + ("; trying fallback providers." if has_fallbacks else "; no fallback providers configured."))
            else:
                log_verbose("TTS: " + provider + " failed (" + raw_error + "); trying next provider.")
    return _build_tts_failure_result(errors, attempted_providers, attempts, persona.get("id") if persona else None)


async def text_to_speech(text, cfg, prefs_path=None, channel=None, overrides=None, disable_fallback=False, timeout_ms=None, agent_id=None, account_id=None):
    synthesis = await synthesize_speech(text=text, cfg=cfg, prefs_path=prefs_path, channel=channel, overrides=overrides, disable_fallback=disable_fallback, timeout_ms=timeout_ms, agent_id=agent_id, account_id=account_id)
    if not synthesis.get("success") or not synthesis.get("audioBuffer") or not synthesis.get("fileExtension"):
        return {"success": False, "error": synthesis.get("error", "TTS conversion failed"), "persona": synthesis.get("persona"), "attemptedProviders": synthesis.get("attemptedProviders"), "attempts": synthesis.get("attempts")}
    audio_buffer = synthesis["audioBuffer"]
    file_extension = synthesis["fileExtension"]
    output_format = synthesis.get("outputFormat")
    transcoded = await _maybe_pre_transcode_for_voice_delivery(channel=channel, target=synthesis.get("target"), audio_buffer=audio_buffer, file_extension=file_extension, output_format=output_format)
    if transcoded:
        audio_buffer = transcoded["audioBuffer"]
        file_extension = transcoded["fileExtension"]
        output_format = transcoded.get("outputFormat")
    temp = temp_workspace_sync(rootDir=resolve_preferred_openclaw_tmp_dir(), prefix="tts-")
    audio_path = temp.write("voice-" + str(int(time.time() * 1000)) + file_extension, audio_buffer)
    schedule_cleanup(temp.dir)
    return {"success": True, "audioPath": audio_path, "latencyMs": synthesis.get("latencyMs"), "provider": synthesis.get("provider"), "persona": synthesis.get("persona"), "fallbackFrom": synthesis.get("fallbackFrom"), "attemptedProviders": synthesis.get("attemptedProviders"), "attempts": synthesis.get("attempts"), "outputFormat": output_format, "voiceCompatible": synthesis.get("voiceCompatible"), "audioAsVoice": _should_deliver_tts_as_voice(channel=channel, target=synthesis.get("target"), voice_compatible=synthesis.get("voiceCompatible"), file_extension=file_extension, output_format=output_format), "target": synthesis.get("target")}


async def stream_speech(text, cfg, prefs_path=None, channel=None, overrides=None, disable_fallback=False, timeout_ms=None, agent_id=None, account_id=None):
    setup = _resolve_tts_request_setup(text=text, cfg=cfg, prefs_path=prefs_path, provider_override=(overrides or {}).get("provider"), disable_fallback=disable_fallback, agent_id=agent_id, channel_id=channel, account_id=account_id)
    if "error" in setup:
        return {"success": False, "error": setup["error"]}
    cfg = setup["cfg"]
    config = setup["config"]
    persona = setup["persona"]
    providers = setup["providers"]
    target = _resolve_tts_synthesis_target(channel)
    errors = []
    attempted_providers = []
    attempts = []
    primary_provider = providers[0]["provider"] if providers else None
    log_verbose("TTS stream: starting with provider " + str(primary_provider) + ", fallbacks: " + (", ".join(e["provider"] for e in providers[1:]) or "none"))
    for entry in providers:
        provider = entry["provider"]
        voice_model = entry.get("voiceModel")
        attempted_providers.append(provider)
        provider_start = int(time.time() * 1000)
        try:
            resolved_provider = _resolve_ready_speech_provider(provider=provider, cfg=cfg, config=config, persona=persona, voice_model=voice_model)
            if resolved_provider["kind"] == "skip":
                errors.append(resolved_provider["message"])
                attempt = {"provider": provider, "outcome": "skipped", "reasonCode": resolved_provider["reasonCode"], "persona": persona.get("id") if persona else None, "error": resolved_provider["message"]}
                if "personaBinding" in resolved_provider:
                    attempt["personaBinding"] = resolved_provider["personaBinding"]
                attempts.append(attempt)
                log_verbose("TTS stream: provider " + provider + " skipped (" + resolved_provider["message"] + ")")
                continue
            stream_fn = resolved_provider["provider"].get("streamSynthesize")
            if not stream_fn:
                message = provider + " does not support streaming TTS"
                errors.append(message)
                attempts.append({"provider": provider, "outcome": "skipped", "reasonCode": "unsupported_for_streaming", "persona": persona.get("id") if persona else None, "personaBinding": resolved_provider["personaBinding"], "error": message})
                log_verbose("TTS stream: provider " + provider + " skipped (" + message + ")")
                continue
            timeout = _resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider["provider"], timeout_ms=timeout_ms or (voice_model or {}).get("timeoutMs"))
            prepared = await _prepare_speech_synthesis(provider=resolved_provider["provider"], text=text, cfg=cfg, provider_config=resolved_provider["providerConfig"], provider_overrides=(overrides or {}).get("providerOverrides", {}).get(resolved_provider["provider"]["id"]), persona=resolved_provider["synthesisPersona"], persona_provider_config=resolved_provider.get("personaProviderConfig"), target=target, timeout_ms=timeout)
            synthesis = await stream_fn(text=prepared["text"], cfg=cfg, providerConfig=prepared["providerConfig"], target=target, providerOverrides=prepared["providerOverrides"], timeoutMs=timeout)
            latency_ms = int(time.time() * 1000) - provider_start
            attempts.append({"provider": provider, "outcome": "success", "reasonCode": "success", "persona": persona.get("id") if persona else None, "personaBinding": resolved_provider["personaBinding"], "latencyMs": latency_ms})
            return {"success": True, "audioStream": synthesis.get("audioStream"), "latencyMs": latency_ms, "provider": provider, "providerModel": _resolve_tts_result_model(prepared["providerConfig"], prepared["providerOverrides"]), "providerVoice": _resolve_tts_result_voice(prepared["providerConfig"], prepared["providerOverrides"]), "persona": persona.get("id") if persona else None, "fallbackFrom": primary_provider if provider != primary_provider else None, "attemptedProviders": attempted_providers, "attempts": attempts, "outputFormat": synthesis.get("outputFormat"), "voiceCompatible": synthesis.get("voiceCompatible"), "fileExtension": synthesis.get("fileExtension"), "target": target, "release": synthesis.get("release")}
        except Exception as err:
            error_msg = _format_tts_provider_error(provider, err)
            latency_ms = int(time.time() * 1000) - provider_start
            errors.append(error_msg)
            persona_binding = "applied" if _resolve_persona_provider_config(persona, provider) is not None else ("missing" if persona else "none")
            reason_code = "timeout" if type(err).__name__ == "AbortError" else "provider_error"
            attempts.append({"provider": provider, "outcome": "failed", "reasonCode": reason_code, "latencyMs": latency_ms, "persona": persona.get("id") if persona else None, "personaBinding": persona_binding, "error": error_msg})
            raw_error = _sanitize_tts_error_for_log(err)
            if provider == primary_provider:
                has_fallbacks = len(providers) > 1
                log_verbose("TTS stream: primary provider " + provider + " failed (" + raw_error + ")" + ("; trying fallback providers." if has_fallbacks else "; no fallback providers configured."))
            else:
                log_verbose("TTS stream: " + provider + " failed (" + raw_error + "); trying next provider.")
    return _build_tts_failure_result(errors, attempted_providers, attempts, persona.get("id") if persona else None)


async def text_to_speech_stream(text, cfg, prefs_path=None, channel=None, overrides=None, disable_fallback=False, timeout_ms=None, agent_id=None, account_id=None):
    synthesis = await stream_speech(text=text, cfg=cfg, prefs_path=prefs_path, channel=channel, overrides=overrides, disable_fallback=disable_fallback, timeout_ms=timeout_ms, agent_id=agent_id, account_id=account_id)
    if not synthesis.get("success") or not synthesis.get("audioStream") or not synthesis.get("fileExtension"):
        return {"success": False, "error": synthesis.get("error", "Streaming TTS conversion failed"), "persona": synthesis.get("persona"), "attemptedProviders": synthesis.get("attemptedProviders"), "attempts": synthesis.get("attempts")}
    return synthesis


async def text_to_speech_telephony(text, cfg, prefs_path=None, overrides=None, timeout_ms=None):
    setup = _resolve_tts_request_setup(text=text, cfg=cfg, prefs_path=prefs_path, provider_override=(overrides or {}).get("provider"))
    if "error" in setup:
        return {"success": False, "error": setup["error"]}
    cfg = setup["cfg"]
    config = setup["config"]
    persona = setup["persona"]
    providers = setup["providers"]
    errors = []
    attempted_providers = []
    attempts = []
    primary_provider = providers[0]["provider"] if providers else None
    log_verbose("TTS telephony: starting with provider " + str(primary_provider) + ", fallbacks: " + (", ".join(e["provider"] for e in providers[1:]) or "none"))
    for entry in providers:
        provider = entry["provider"]
        voice_model = entry.get("voiceModel")
        attempted_providers.append(provider)
        provider_start = int(time.time() * 1000)
        try:
            resolved_provider = _resolve_ready_speech_provider(provider=provider, cfg=cfg, config=config, persona=persona, voice_model=voice_model, require_telephony=True)
            if resolved_provider["kind"] == "skip":
                errors.append(resolved_provider["message"])
                attempt = {"provider": provider, "outcome": "skipped", "reasonCode": resolved_provider["reasonCode"], "persona": persona.get("id") if persona else None, "error": resolved_provider["message"]}
                if "personaBinding" in resolved_provider:
                    attempt["personaBinding"] = resolved_provider["personaBinding"]
                attempts.append(attempt)
                log_verbose("TTS telephony: provider " + provider + " skipped (" + resolved_provider["message"] + ")")
                continue
            timeout = _resolve_speech_provider_timeout_ms(config=config, provider=resolved_provider["provider"], timeout_ms=timeout_ms or (voice_model or {}).get("timeoutMs"))
            telephony_fn = resolved_provider["provider"]["synthesizeTelephony"]
            prepared = await _prepare_speech_synthesis(provider=resolved_provider["provider"], text=text, cfg=cfg, provider_config=resolved_provider["providerConfig"], provider_overrides=(overrides or {}).get("providerOverrides", {}).get(resolved_provider["provider"]["id"]), persona=resolved_provider["synthesisPersona"], persona_provider_config=resolved_provider.get("personaProviderConfig"), target="telephony", timeout_ms=timeout)
            synthesis = await telephony_fn(text=prepared["text"], cfg=cfg, providerConfig=prepared["providerConfig"], providerOverrides=prepared["providerOverrides"], timeoutMs=timeout)
            latency_ms = int(time.time() * 1000) - provider_start
            attempts.append({"provider": provider, "outcome": "success", "reasonCode": "success", "persona": persona.get("id") if persona else None, "personaBinding": resolved_provider["personaBinding"], "latencyMs": latency_ms})
            return {"success": True, "audioBuffer": synthesis.get("audioBuffer"), "latencyMs": latency_ms, "provider": provider, "providerModel": _resolve_tts_result_model(prepared["providerConfig"], prepared["providerOverrides"]), "providerVoice": _resolve_tts_result_voice(prepared["providerConfig"], prepared["providerOverrides"]), "persona": persona.get("id") if persona else None, "fallbackFrom": primary_provider if provider != primary_provider else None, "attemptedProviders": attempted_providers, "attempts": attempts, "outputFormat": synthesis.get("outputFormat"), "sampleRate": synthesis.get("sampleRate")}
        except Exception as err:
            error_msg = _format_tts_provider_error(provider, err)
            latency_ms = int(time.time() * 1000) - provider_start
            errors.append(error_msg)
            persona_binding = "applied" if _resolve_persona_provider_config(persona, provider) is not None else ("missing" if persona else "none")
            reason_code = "timeout" if type(err).__name__ == "AbortError" else "provider_error"
            attempts.append({"provider": provider, "outcome": "failed", "reasonCode": reason_code, "latencyMs": latency_ms, "persona": persona.get("id") if persona else None, "personaBinding": persona_binding, "error": error_msg})
            raw_error = _sanitize_tts_error_for_log(err)
            if provider == primary_provider:
                has_fallbacks = len(providers) > 1
                log_verbose("TTS telephony: primary provider " + provider + " failed (" + raw_error + ")" + ("; trying fallback providers." if has_fallbacks else "; no fallback providers configured."))
            else:
                log_verbose("TTS telephony: " + provider + " failed (" + raw_error + "); trying next provider.")
    return _build_tts_failure_result(errors, attempted_providers, attempts, persona.get("id") if persona else None)


async def list_speech_voices(provider, cfg=None, config=None, api_key=None, base_url=None):
    effective_cfg = _resolve_tts_runtime_config(cfg) if cfg else None
    provider_id = canonicalize_speech_provider_id(provider, effective_cfg)
    if not provider_id:
        raise Exception("speech provider id is required")
    config = config or (resolve_tts_config(effective_cfg) if effective_cfg else None)
    if not config:
        raise Exception("speech provider " + provider_id + " requires cfg or resolved config")
    resolved_provider = get_speech_provider(provider_id, effective_cfg)
    if not resolved_provider:
        raise Exception("speech provider " + provider_id + " is not registered")
    list_voices_fn = resolved_provider.get("listVoices")
    if not list_voices_fn:
        raise Exception("speech provider " + provider_id + " does not support voice listing")
    return await list_voices_fn(cfg=effective_cfg, providerConfig=get_resolved_speech_provider_config(config, resolved_provider["id"], effective_cfg), apiKey=api_key, baseUrl=base_url)


async def maybe_apply_tts_to_payload(payload, cfg, channel=None, kind=None, inbound_audio=None, tts_auto=None, agent_id=None, account_id=None):
    if payload.get("isCompactionNotice"):
        return payload
    cfg = _resolve_tts_runtime_config(cfg)
    state = _resolve_effective_tts_auto_state(cfg=cfg, session_auto=tts_auto, agent_id=agent_id, channel_id=channel, account_id=account_id)
    auto_mode = state["autoMode"]
    prefs_path = state["prefsPath"]
    if auto_mode == "off":
        return payload
    config = resolve_tts_config(cfg, {"agentId": agent_id, "channelId": channel, "accountId": account_id})
    active_provider = get_tts_provider(config, prefs_path)
    reply = resolve_sendable_outbound_reply_parts(payload)
    text = reply.get("text", "")
    directives = parse_tts_directives(text, config["modelOverrides"], cfg=cfg, providerConfigs=config["providerConfigs"], preferredProviderId=active_provider)
    if directives.get("warnings"):
        log_verbose("TTS: ignored directive overrides (" + "; ".join(directives["warnings"]) + ")")
    if is_verbose():
        effective_provider = active_provider
        if directives.get("overrides", {}).get("provider"):
            effective_provider = canonicalize_speech_provider_id(directives["overrides"]["provider"], cfg) or active_provider
        log_verbose("TTS: auto mode enabled (" + auto_mode + "), channel=" + str(channel) + ", selected provider=" + str(effective_provider) + ", config.provider=" + str(config["provider"]) + ", config.providerSource=" + str(config["providerSource"]))
    cleaned_text = directives.get("cleanedText", "")
    trimmed_cleaned = cleaned_text.strip()
    visible_text = trimmed_cleaned if trimmed_cleaned else ""
    explicit_tts_text = (directives.get("ttsText") or "").strip()
    tts_text = explicit_tts_text or visible_text
    if visible_text == text.strip():
        next_payload = payload
    else:
        next_payload = {**payload, "text": visible_text if visible_text else None}
    if auto_mode == "tagged" and not directives.get("hasDirective"):
        return next_payload
    if auto_mode == "inbound" and inbound_audio is not True:
        return next_payload
    mode = config.get("mode") or "final"
    if mode == "final" and kind and kind != "final":
        return next_payload
    if not tts_text.strip():
        return next_payload
    if reply.get("hasMedia") or _has_legacy_final_media_directive(text):
        return next_payload
    if not explicit_tts_text and len(tts_text.strip()) < 10:
        return next_payload
    max_length = get_tts_max_length(prefs_path)
    text_for_audio = tts_text.strip()
    was_summarized = False
    if len(text_for_audio) > max_length:
        if not is_summarization_enabled(prefs_path):
            log_verbose("TTS: truncating long text (" + str(len(text_for_audio)) + " > " + str(max_length) + "), summarization disabled.")
            text_for_audio = text_for_audio[:max_length - 3] + "..."
        else:
            try:
                summary = await summarize_text(text=text_for_audio, targetLength=max_length, cfg=cfg, config=config, timeoutMs=config["timeoutMs"])
                text_for_audio = summary["summary"]
                was_summarized = True
                if len(text_for_audio) > config["maxTextLength"]:
                    log_verbose("TTS: summary exceeded hard limit (" + str(len(text_for_audio)) + " > " + str(config["maxTextLength"]) + "); truncating.")
                    text_for_audio = text_for_audio[:config["maxTextLength"] - 3] + "..."
            except Exception as error:
                log_verbose("TTS: summarization failed, truncating instead: " + str(error))
                text_for_audio = text_for_audio[:max_length - 3] + "..."
    text_for_audio = strip_markdown(text_for_audio).strip()
    if not text_for_audio:
        return next_payload
    if not explicit_tts_text and len(text_for_audio) < 10:
        return next_payload
    tts_start = int(time.time() * 1000)
    result = await text_to_speech(text=text_for_audio, cfg=cfg, prefs_path=prefs_path, channel=channel, overrides=directives.get("overrides"), agentId=agent_id, accountId=account_id)
    if result.get("success") and result.get("audioPath"):
        global _last_tts_attempt
        _last_tts_attempt = {"timestamp": int(time.time() * 1000), "success": True, "textLength": len(text), "summarized": was_summarized, "provider": result.get("provider"), "persona": result.get("persona"), "fallbackFrom": result.get("fallbackFrom"), "attemptedProviders": result.get("attemptedProviders"), "attempts": result.get("attempts"), "latencyMs": result.get("latencyMs")}
        payload_with_audio = {**next_payload, "mediaUrl": result["audioPath"], "audioAsVoice": result.get("audioAsVoice") or payload.get("audioAsVoice"), "spokenText": text_for_audio, "trustedLocalMedia": True}
        if next_payload.get("text") and next_payload["text"].strip():
            return mark_reply_payload_as_tts_supplement(payload_with_audio)
        return payload_with_audio
    global _last_tts_attempt
    _last_tts_attempt = {"timestamp": int(time.time() * 1000), "success": False, "textLength": len(text), "summarized": was_summarized, "persona": result.get("persona"), "attemptedProviders": result.get("attemptedProviders"), "attempts": result.get("attempts"), "error": result.get("error")}
    latency = int(time.time() * 1000) - tts_start
    log_verbose("TTS: conversion failed after " + str(latency) + "ms (" + str(result.get("error", "unknown")) + ").")
    return next_payload


test_api = {
    "parseTtsDirectives": parse_tts_directives,
    "resolveModelOverridePolicy": _resolve_model_override_policy,
    "supportsNativeVoiceNoteTts": _supports_native_voice_note_tts,
    "supportsTranscodedVoiceNoteTts": _supports_transcoded_voice_note_tts,
    "resolveTtsSynthesisTarget": _resolve_tts_synthesis_target,
    "shouldDeliverTtsAsVoice": _should_deliver_tts_as_voice,
    "summarizeText": summarize_text,
    "getResolvedSpeechProviderConfig": get_resolved_speech_provider_config,
    "formatTtsProviderError": _format_tts_provider_error,
    "sanitizeTtsErrorForLog": _sanitize_tts_error_for_log,
}

_test = test_api


__all__ = [
    "TtsUserPrefs", "TtsAttemptReasonCode", "TtsProviderAttempt", "TtsResult",
    "TtsSynthesisResult", "TtsStreamResult", "TtsSynthesisStreamResult",
    "TtsTelephonyResult", "TtsStatusEntry",
    "resolve_tts_config", "resolve_tts_prefs_path", "resolve_tts_auto_mode",
    "build_tts_system_prompt_hint", "is_tts_enabled", "set_tts_auto_mode",
    "set_tts_enabled", "get_tts_provider", "get_tts_persona", "list_tts_personas",
    "set_tts_persona", "set_tts_provider", "get_tts_max_length", "set_tts_max_length",
    "is_summarization_enabled", "set_summarization_enabled",
    "get_last_tts_attempt", "set_last_tts_attempt", "resolve_tts_provider_order",
    "is_tts_provider_configured", "get_resolved_speech_provider_config",
    "resolve_explicit_tts_overrides", "text_to_speech", "synthesize_speech",
    "stream_speech", "text_to_speech_stream", "text_to_speech_telephony",
    "list_speech_voices", "maybe_apply_tts_to_payload", "test_api", "_test",
]
