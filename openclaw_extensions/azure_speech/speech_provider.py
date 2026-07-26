"""Azure Speech provider descriptor for the speech-core runtime."""

from __future__ import annotations

import math
import os
from typing import Any

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import as_record, normalize_optional_string
from openclaw_extensions.azure_speech.tts import (
    DEFAULT_AZURE_SPEECH_AUDIO_FORMAT,
    DEFAULT_AZURE_SPEECH_LANG,
    DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT,
    DEFAULT_AZURE_SPEECH_VOICE,
    DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT,
    azure_speech_tts,
    infer_azure_speech_file_extension,
    is_azure_speech_voice_compatible,
    list_azure_speech_voices,
    normalize_azure_speech_base_url,
)

DEFAULT_GENERATED_AUDIO_MAX_BYTES = 16 * 1024 * 1024


def _as_finite_number(value: Any) -> int | float | None:
    if not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return value


def _read_azure_speech_env_api_key() -> str | None:
    return (
        normalize_optional_string(os.environ.get("AZURE_SPEECH_KEY"))
        or normalize_optional_string(os.environ.get("AZURE_SPEECH_API_KEY"))
        or normalize_optional_string(os.environ.get("SPEECH_KEY"))
    )


def _read_azure_speech_env_region() -> str | None:
    return normalize_optional_string(os.environ.get("AZURE_SPEECH_REGION")) or normalize_optional_string(
        os.environ.get("SPEECH_REGION")
    )


def _read_azure_speech_env_endpoint() -> str | None:
    return normalize_optional_string(os.environ.get("AZURE_SPEECH_ENDPOINT"))


def _resolve_azure_speech_config_record(
    raw_config: dict[str, Any],
) -> dict[str, Any] | None:
    providers = as_record(raw_config.get("providers"))
    return (
        as_record(providers.get("azure-speech") if providers else None)
        or as_record(providers.get("azure") if providers else None)
        or as_record(raw_config.get("azure-speech"))
        or as_record(raw_config.get("azure"))
    )


def _normalize_azure_speech_provider_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    raw = _resolve_azure_speech_config_record(raw_config)
    region = normalize_optional_string(raw.get("region") if raw else None) or _read_azure_speech_env_region()
    endpoint = (
        normalize_optional_string(raw.get("endpoint") if raw else None) or _read_azure_speech_env_endpoint()
    )
    resolved_base_url = normalize_azure_speech_base_url(
        base_url=normalize_optional_string(raw.get("baseUrl") if raw else None),
        endpoint=endpoint,
        region=region,
    )
    return {
        "apiKey": normalize_secret_input_string(raw.get("apiKey") if raw else None),
        "region": region,
        "endpoint": endpoint,
        "baseUrl": resolved_base_url,
        "voice": normalize_optional_string(raw.get("voice") if raw else None)
        or normalize_optional_string(raw.get("voiceId") if raw else None)
        or DEFAULT_AZURE_SPEECH_VOICE,
        "lang": normalize_optional_string(raw.get("lang") if raw else None)
        or normalize_optional_string(raw.get("languageCode") if raw else None)
        or DEFAULT_AZURE_SPEECH_LANG,
        "outputFormat": normalize_optional_string(raw.get("outputFormat") if raw else None)
        or DEFAULT_AZURE_SPEECH_AUDIO_FORMAT,
        "voiceNoteOutputFormat": normalize_optional_string(
            raw.get("voiceNoteOutputFormat") if raw else None
        )
        or DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT,
        "timeoutMs": _as_finite_number(raw.get("timeoutMs") if raw else None),
    }


def _read_azure_speech_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = _normalize_azure_speech_provider_config({})
    region = normalize_optional_string(config.get("region")) or defaults["region"]
    endpoint = normalize_optional_string(config.get("endpoint")) or defaults["endpoint"]
    resolved_base_url = normalize_azure_speech_base_url(
        base_url=normalize_optional_string(config.get("baseUrl")) or defaults["baseUrl"],
        endpoint=endpoint,
        region=region,
    )
    timeout_ms = _as_finite_number(config.get("timeoutMs"))
    return {
        "apiKey": normalize_optional_string(config.get("apiKey")) or defaults["apiKey"],
        "region": region,
        "endpoint": endpoint,
        "baseUrl": resolved_base_url,
        "voice": normalize_optional_string(config.get("voice"))
        or normalize_optional_string(config.get("voiceId"))
        or defaults["voice"],
        "lang": normalize_optional_string(config.get("lang"))
        or normalize_optional_string(config.get("languageCode"))
        or defaults["lang"],
        "outputFormat": normalize_optional_string(config.get("outputFormat")) or defaults["outputFormat"],
        "voiceNoteOutputFormat": normalize_optional_string(config.get("voiceNoteOutputFormat"))
        or defaults["voiceNoteOutputFormat"],
        "timeoutMs": timeout_ms if timeout_ms is not None else defaults["timeoutMs"],
    }


def _read_azure_speech_overrides(overrides: dict[str, Any] | None) -> dict[str, Any]:
    if not overrides:
        return {}
    return {
        "voice": normalize_optional_string(overrides.get("voice"))
        or normalize_optional_string(overrides.get("voiceId")),
        "lang": normalize_optional_string(overrides.get("lang"))
        or normalize_optional_string(overrides.get("languageCode")),
        "outputFormat": normalize_optional_string(overrides.get("outputFormat")),
    }


def _parse_directive_token(ctx: dict[str, Any]) -> dict[str, Any]:
    key = str(ctx.get("key") or "").lower()
    policy = ctx.get("policy") if isinstance(ctx.get("policy"), dict) else {}
    current_overrides = ctx.get("currentOverrides")
    overrides = dict(current_overrides) if isinstance(current_overrides, dict) else {}

    if key in {
        "voice",
        "voiceid",
        "voice_id",
        "azure_voice",
        "azurevoice",
        "azure_speech_voice",
    }:
        if not policy.get("allowVoice"):
            return {"handled": True}
        overrides["voice"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}

    if key in {
        "lang",
        "language",
        "language_code",
        "languagecode",
        "azure_lang",
        "azure_language",
    }:
        if not policy.get("allowVoiceSettings"):
            return {"handled": True}
        overrides["lang"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}

    if key in {
        "output_format",
        "outputformat",
        "azure_format",
        "azure_output_format",
    }:
        if not policy.get("allowVoiceSettings"):
            return {"handled": True}
        overrides["outputFormat"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}

    return {"handled": False}


def _resolve_api_key(config: dict[str, Any]) -> str | None:
    return normalize_optional_string(config.get("apiKey")) or _read_azure_speech_env_api_key()


def _resolve_timeout_ms(config: dict[str, Any], timeout_ms: int) -> int:
    configured = config.get("timeoutMs")
    if isinstance(configured, (int, float)) and math.isfinite(configured):
        return int(configured)
    return timeout_ms


def _resolve_generated_audio_max_bytes(req: dict[str, Any]) -> int:
    cfg = req.get("cfg") if isinstance(req.get("cfg"), dict) else {}
    agents = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    configured = defaults.get("mediaMaxMb")
    if isinstance(configured, (int, float)) and math.isfinite(configured) and configured > 0:
        return int(configured * 1024 * 1024)
    return DEFAULT_GENERATED_AUDIO_MAX_BYTES


def build_azure_speech_provider() -> dict[str, Any]:
    def resolve_talk_config(params: dict[str, Any]) -> dict[str, Any]:
        base_tts_config = params.get("baseTtsConfig")
        talk_provider_config = params.get("talkProviderConfig")
        base = _normalize_azure_speech_provider_config(
            base_tts_config if isinstance(base_tts_config, dict) else {}
        )
        talk = talk_provider_config if isinstance(talk_provider_config, dict) else {}
        api_key = (
            None
            if talk.get("apiKey") is None
            else normalize_secret_input_string(talk.get("apiKey"))
        )
        region = normalize_optional_string(talk.get("region"))
        endpoint = normalize_optional_string(talk.get("endpoint")) or normalize_optional_string(
            talk.get("baseUrl")
        )
        resolved_base_url = normalize_azure_speech_base_url(
            base_url=normalize_optional_string(talk.get("baseUrl")),
            endpoint=endpoint,
            region=region or base["region"],
        )
        result = dict(base)
        if api_key is not None:
            result["apiKey"] = api_key
        if region is not None:
            result["region"] = region
        if endpoint is not None:
            result["endpoint"] = endpoint
        if resolved_base_url is not None:
            result["baseUrl"] = resolved_base_url
        voice_id = normalize_optional_string(talk.get("voiceId"))
        if voice_id is not None:
            result["voice"] = voice_id
        language_code = normalize_optional_string(talk.get("languageCode"))
        if language_code is not None:
            result["lang"] = language_code
        output_format = normalize_optional_string(talk.get("outputFormat"))
        if output_format is not None:
            result["outputFormat"] = output_format
        return result

    def resolve_talk_overrides(params: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        voice_id = normalize_optional_string(params.get("voiceId"))
        if voice_id is not None:
            result["voice"] = voice_id
        language_code = normalize_optional_string(params.get("languageCode"))
        if language_code is not None:
            result["lang"] = language_code
        output_format = normalize_optional_string(params.get("outputFormat"))
        if output_format is not None:
            result["outputFormat"] = output_format
        return result

    async def list_voices(req: dict[str, Any]) -> list[dict[str, Any]]:
        provider_config = req.get("providerConfig")
        config = (
            _read_azure_speech_provider_config(provider_config)
            if isinstance(provider_config, dict)
            else None
        )
        api_key = normalize_optional_string(req.get("apiKey")) or (
            _resolve_api_key(config) if config else _read_azure_speech_env_api_key()
        )
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        return await list_azure_speech_voices(
            api_key=api_key,
            base_url=normalize_optional_string(req.get("baseUrl")) or (config["baseUrl"] if config else None),
            endpoint=config["endpoint"] if config else None,
            region=(config["region"] if config else None) or _read_azure_speech_env_region(),
            timeout_ms=config["timeoutMs"] if config else None,
        )

    def is_configured(params: dict[str, Any]) -> bool:
        provider_config = params.get("providerConfig")
        config = _read_azure_speech_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        return bool(
            _resolve_api_key(config) and (config.get("baseUrl") or config.get("region") or config.get("endpoint"))
        )

    async def synthesize(req: dict[str, Any]) -> dict[str, Any]:
        provider_config = req.get("providerConfig")
        config = _read_azure_speech_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        overrides = _read_azure_speech_overrides(
            req.get("providerOverrides") if isinstance(req.get("providerOverrides"), dict) else None
        )
        api_key = _resolve_api_key(config)
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        output_format = overrides.get("outputFormat") or (
            config["voiceNoteOutputFormat"]
            if req.get("target") == "voice-note"
            else config["outputFormat"]
        )
        audio_buffer = await azure_speech_tts(
            text=str(req.get("text") or ""),
            api_key=api_key,
            base_url=config.get("baseUrl"),
            endpoint=config.get("endpoint"),
            region=config.get("region"),
            voice=overrides.get("voice") or config["voice"],
            lang=overrides.get("lang") or config["lang"],
            output_format=output_format,
            timeout_ms=_resolve_timeout_ms(config, int(req.get("timeoutMs") or 0)),
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "fileExtension": infer_azure_speech_file_extension(output_format),
            "voiceCompatible": is_azure_speech_voice_compatible(output_format),
        }

    async def synthesize_telephony(req: dict[str, Any]) -> dict[str, Any]:
        provider_config = req.get("providerConfig")
        config = _read_azure_speech_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        overrides = _read_azure_speech_overrides(
            req.get("providerOverrides") if isinstance(req.get("providerOverrides"), dict) else None
        )
        api_key = _resolve_api_key(config)
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        sample_rate = 8_000
        audio_buffer = await azure_speech_tts(
            text=str(req.get("text") or ""),
            api_key=api_key,
            base_url=config.get("baseUrl"),
            endpoint=config.get("endpoint"),
            region=config.get("region"),
            voice=overrides.get("voice") or config["voice"],
            lang=overrides.get("lang") or config["lang"],
            output_format=DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT,
            timeout_ms=_resolve_timeout_ms(config, int(req.get("timeoutMs") or 0)),
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT,
            "sampleRate": sample_rate,
        }

    return {
        "id": "azure-speech",
        "label": "Azure Speech",
        "aliases": ["azure"],
        "autoSelectOrder": 30,
        "resolveConfig": lambda params: _normalize_azure_speech_provider_config(
            params.get("rawConfig") if isinstance(params.get("rawConfig"), dict) else {}
        ),
        "parseDirectiveToken": _parse_directive_token,
        "resolveTalkConfig": resolve_talk_config,
        "resolveTalkOverrides": resolve_talk_overrides,
        "listVoices": list_voices,
        "isConfigured": is_configured,
        "synthesize": synthesize,
        "synthesizeTelephony": synthesize_telephony,
    }
