from __future__ import annotations

from typing import Any

from openclaw.config.secrets import coerce_secret_ref


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_fast_mode(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "on", "true", "yes"}
    return None


def _normalize_think_level(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"none", "low", "medium", "high"}:
        return normalized
    return None


def _normalize_talk_secret_input(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    ref = coerce_secret_ref(value)
    return ref.id if ref else None


def _normalize_silence_timeout_ms(value: Any) -> int | None:
    if not isinstance(value, int) or value <= 0:
        return None
    return value


def _normalize_talk_provider_config(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    provider: dict[str, Any] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        if key == "apiKey":
            normalized = _normalize_talk_secret_input(raw)
            if normalized is not None:
                provider["apiKey"] = normalized
            continue
        provider[key] = raw
    return provider if provider else None


def _normalize_talk_providers(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None
    providers: dict[str, dict[str, Any]] = {}
    for raw_id, provider_config in value.items():
        provider_id = _normalize_optional_string(raw_id)
        if not provider_id:
            continue
        normalized = _normalize_talk_provider_config(provider_config)
        if not normalized:
            continue
        providers[provider_id] = dict(providers.get(provider_id, {}), **normalized)
    return providers if providers else None


def _normalize_talk_realtime_config(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source = value
    normalized: dict[str, Any] = {}
    provider = _normalize_optional_string(source.get("provider"))
    if provider:
        normalized["provider"] = provider
    providers = _normalize_talk_providers(source.get("providers"))
    if providers:
        normalized["providers"] = providers
    model = _normalize_optional_string(source.get("model"))
    if model:
        normalized["model"] = model
    voice = _normalize_optional_string(source.get("voice"))
    speaker_voice = _normalize_optional_string(source.get("speakerVoice")) or voice
    speaker_voice_id = _normalize_optional_string(source.get("speakerVoiceId"))
    if speaker_voice:
        normalized["speakerVoice"] = speaker_voice
    if speaker_voice_id:
        normalized["speakerVoiceId"] = speaker_voice_id
    if voice:
        normalized["voice"] = voice
    instructions = _normalize_optional_string(source.get("instructions"))
    if instructions:
        normalized["instructions"] = instructions
    mode = source.get("mode")
    if mode in {"realtime", "stt-tts", "transcription"}:
        normalized["mode"] = mode
    transport = source.get("transport")
    if transport in {"webrtc", "provider-websocket", "gateway-relay", "managed-room"}:
        normalized["transport"] = transport
    brain = source.get("brain")
    if brain in {"agent-consult", "direct-tools", "none"}:
        normalized["brain"] = brain
    consult_routing = source.get("consultRouting")
    if consult_routing in {"provider-direct", "force-agent-consult"}:
        normalized["consultRouting"] = consult_routing
    return normalized if normalized else None


def _active_provider_from_talk(talk: dict[str, Any]) -> str | None:
    provider = _normalize_optional_string(talk.get("provider"))
    providers = talk.get("providers")
    if provider:
        if providers and provider not in providers:
            return None
        return provider
    if isinstance(providers, dict) and len(providers) == 1:
        return next(iter(providers))
    return None


def normalize_talk_section(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source = value
    normalized: dict[str, Any] = {}
    speech_locale = _normalize_optional_string(source.get("speechLocale"))
    if speech_locale:
        normalized["speechLocale"] = speech_locale
    if isinstance(source.get("interruptOnSpeech"), bool):
        normalized["interruptOnSpeech"] = source["interruptOnSpeech"]
    consult_level = _normalize_think_level(_normalize_optional_string(source.get("consultThinkingLevel")))
    if consult_level:
        normalized["consultThinkingLevel"] = consult_level
    raw_fast = source.get("consultFastMode")
    if isinstance(raw_fast, (bool, str)):
        fast_mode = _normalize_fast_mode(raw_fast)
        if isinstance(fast_mode, bool):
            normalized["consultFastMode"] = fast_mode
    silence = _normalize_silence_timeout_ms(source.get("silenceTimeoutMs"))
    if silence is not None:
        normalized["silenceTimeoutMs"] = silence
    providers = _normalize_talk_providers(source.get("providers"))
    realtime = _normalize_talk_realtime_config(source.get("realtime"))
    provider = _normalize_optional_string(source.get("provider"))
    if providers:
        normalized["providers"] = providers
    if realtime:
        normalized["realtime"] = realtime
    if provider:
        normalized["provider"] = provider
    return normalized if normalized else None


def normalize_talk_config(config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("talk"):
        return config
    normalized_talk = normalize_talk_section(config["talk"])
    if not normalized_talk:
        return config
    result = dict(config)
    result["talk"] = normalized_talk
    return result


def resolve_active_talk_provider_config(
    talk: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = normalize_talk_section(talk)
    if not normalized:
        return None
    provider = _active_provider_from_talk(normalized)
    if not provider:
        return None
    return {"provider": provider, "config": (normalized.get("providers") or {}).get(provider, {})}


def build_talk_config_response(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    normalized = normalize_talk_section(value)
    if not normalized:
        return None
    payload: dict[str, Any] = {}
    if isinstance(normalized.get("interruptOnSpeech"), bool):
        payload["interruptOnSpeech"] = normalized["interruptOnSpeech"]
    if isinstance(normalized.get("silenceTimeoutMs"), int):
        payload["silenceTimeoutMs"] = normalized["silenceTimeoutMs"]
    if isinstance(normalized.get("consultThinkingLevel"), str):
        payload["consultThinkingLevel"] = normalized["consultThinkingLevel"]
    if isinstance(normalized.get("consultFastMode"), bool):
        payload["consultFastMode"] = normalized["consultFastMode"]
    if isinstance(normalized.get("speechLocale"), str):
        payload["speechLocale"] = normalized["speechLocale"]
    if normalized.get("providers"):
        payload["providers"] = normalized["providers"]
    if normalized.get("realtime"):
        payload["realtime"] = normalized["realtime"]
    resolved = resolve_active_talk_provider_config(normalized)
    if resolved:
        payload["provider"] = resolved["provider"]
        payload["resolved"] = resolved
    return payload if payload else None
