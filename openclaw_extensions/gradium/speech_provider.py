"""Gradium speech provider plugin integration."""

from __future__ import annotations

import os
from typing import Any

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import as_record, normalize_optional_string
from openclaw_extensions.gradium.shared import (
    DEFAULT_GRADIUM_VOICE_ID,
    GRADIUM_VOICES,
    normalize_gradium_base_url,
)
from openclaw_extensions.gradium.tts import gradium_tts

DEFAULT_GENERATED_AUDIO_MAX_BYTES = 16 * 1024 * 1024


def _normalize_gradium_provider_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    providers = as_record(raw_config.get("providers"))
    raw = as_record(providers.get("gradium") if providers else None) or as_record(
        raw_config.get("gradium")
    )
    return {
        "apiKey": normalize_secret_input_string(raw.get("apiKey") if raw else None),
        "baseUrl": normalize_gradium_base_url(
            normalize_optional_string(raw.get("baseUrl") if raw else None)
        ),
        "voiceId": normalize_optional_string(raw.get("voiceId") if raw else None)
        or DEFAULT_GRADIUM_VOICE_ID,
    }


def _read_gradium_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = _normalize_gradium_provider_config({})
    return {
        "apiKey": normalize_optional_string(config.get("apiKey")) or defaults["apiKey"],
        "baseUrl": normalize_gradium_base_url(
            normalize_optional_string(config.get("baseUrl")) or defaults["baseUrl"]
        ),
        "voiceId": normalize_optional_string(config.get("voiceId")) or defaults["voiceId"],
    }


def _resolve_generated_audio_max_bytes(req: dict[str, Any]) -> int:
    cfg = req.get("cfg") if isinstance(req.get("cfg"), dict) else {}
    agents = cfg.get("agents") if isinstance(cfg.get("agents"), dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    configured = defaults.get("mediaMaxMb")
    if isinstance(configured, (int, float)) and configured > 0:
        return int(configured * 1024 * 1024)
    return DEFAULT_GENERATED_AUDIO_MAX_BYTES


def _parse_directive_token(ctx: dict[str, Any]) -> dict[str, Any]:
    key = str(ctx.get("key") or "").lower()
    if key in {"voice", "voice_id", "voiceid", "gradium_voice", "gradiumvoice"}:
        policy = ctx.get("policy") if isinstance(ctx.get("policy"), dict) else {}
        if not policy.get("allowVoice"):
            return {"handled": True}
        current_overrides = ctx.get("currentOverrides")
        overrides = dict(current_overrides) if isinstance(current_overrides, dict) else {}
        overrides["voiceId"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}
    return {"handled": False}


def build_gradium_speech_provider() -> dict[str, Any]:
    async def list_voices() -> list[dict[str, str]]:
        return [{"id": voice["id"], "name": voice["name"]} for voice in GRADIUM_VOICES]

    def is_configured(params: dict[str, Any]) -> bool:
        provider_config = params.get("providerConfig")
        config = _read_gradium_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        return bool(config.get("apiKey") or os.environ.get("GRADIUM_API_KEY"))

    async def synthesize(req: dict[str, Any]) -> dict[str, Any]:
        provider_config = req.get("providerConfig")
        config = _read_gradium_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        overrides = req.get("providerOverrides")
        provider_overrides = overrides if isinstance(overrides, dict) else {}
        api_key = config.get("apiKey") or os.environ.get("GRADIUM_API_KEY")
        if not api_key:
            raise RuntimeError("Gradium API key missing")
        wants_voice_note = req.get("target") == "voice-note"
        output_format = "opus" if wants_voice_note else "wav"
        audio_buffer = await gradium_tts(
            text=str(req.get("text") or ""),
            api_key=api_key,
            base_url=config["baseUrl"],
            voice_id=normalize_optional_string(provider_overrides.get("voiceId"))
            or config["voiceId"],
            output_format=output_format,
            timeout_ms=int(req.get("timeoutMs") or 0),
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "fileExtension": ".opus" if wants_voice_note else ".wav",
            "voiceCompatible": wants_voice_note,
        }

    async def synthesize_telephony(req: dict[str, Any]) -> dict[str, Any]:
        provider_config = req.get("providerConfig")
        config = _read_gradium_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        overrides = req.get("providerOverrides")
        provider_overrides = overrides if isinstance(overrides, dict) else {}
        api_key = config.get("apiKey") or os.environ.get("GRADIUM_API_KEY")
        if not api_key:
            raise RuntimeError("Gradium API key missing")
        output_format = "ulaw_8000"
        sample_rate = 8_000
        audio_buffer = await gradium_tts(
            text=str(req.get("text") or ""),
            api_key=api_key,
            base_url=config["baseUrl"],
            voice_id=normalize_optional_string(provider_overrides.get("voiceId"))
            or config["voiceId"],
            output_format=output_format,
            timeout_ms=int(req.get("timeoutMs") or 0),
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "sampleRate": sample_rate,
        }

    return {
        "id": "gradium",
        "label": "Gradium",
        "autoSelectOrder": 30,
        "voices": [voice["id"] for voice in GRADIUM_VOICES],
        "resolveConfig": lambda params: _normalize_gradium_provider_config(
            params.get("rawConfig") if isinstance(params.get("rawConfig"), dict) else {}
        ),
        "parseDirectiveToken": _parse_directive_token,
        "listVoices": list_voices,
        "isConfigured": is_configured,
        "synthesize": synthesize,
        "synthesizeTelephony": synthesize_telephony,
    }
