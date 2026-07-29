import os
from typing import Any, Optional

from .._sdk import normalize_secret_input
from .shared import DEFAULT_GRADIUM_VOICE_ID, GRADIUM_VOICES, normalize_gradium_base_url
from .tts import gradium_tts

DEFAULT_GENERATED_AUDIO_MAX_BYTES = 16 * 1024 * 1024


def _as_object(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _trim_to_undefined(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _normalize_gradium_provider_config(raw_config: dict) -> dict:
    providers = _as_object(raw_config.get("providers"))
    raw = _as_object(providers.get("gradium")) or _as_object(raw_config.get("gradium"))
    return {
        "apiKey": normalize_secret_input(raw.get("apiKey")),
        "baseUrl": normalize_gradium_base_url(_trim_to_undefined(raw.get("baseUrl"))),
        "voiceId": _trim_to_undefined(raw.get("voiceId")) or DEFAULT_GRADIUM_VOICE_ID,
    }


def _read_gradium_provider_config(config: dict) -> dict:
    defaults = _normalize_gradium_provider_config({})
    return {
        "apiKey": _trim_to_undefined(config.get("apiKey")) or defaults["apiKey"],
        "baseUrl": normalize_gradium_base_url(_trim_to_undefined(config.get("baseUrl")) or defaults["baseUrl"]),
        "voiceId": _trim_to_undefined(config.get("voiceId")) or defaults["voiceId"],
    }


def _resolve_generated_audio_max_bytes(req: dict) -> int:
    configured = req.get("cfg", {}).get("agents", {}).get("defaults", {}).get("mediaMaxMb")
    if isinstance(configured, (int, float)) and configured == configured and configured > 0:
        return int(configured * 1024 * 1024)
    return DEFAULT_GENERATED_AUDIO_MAX_BYTES


def _parse_directive_token(ctx: dict) -> dict:
    key = ctx.get("key")
    if key in ("voice", "voice_id", "voiceid", "gradium_voice", "gradiumvoice"):
        if not ctx.get("policy", {}).get("allowVoice"):
            return {"handled": True}
        overrides = dict(ctx.get("currentOverrides", {}))
        overrides["voiceId"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}
    return {"handled": False}


def build_gradium_speech_provider() -> dict:
    async def list_voices():
        return [{"id": v["id"], "name": v["name"]} for v in GRADIUM_VOICES]

    def is_configured(req: dict) -> bool:
        config = _read_gradium_provider_config(req.get("providerConfig", {}))
        return bool(config["apiKey"] or os.environ.get("GRADIUM_API_KEY"))

    async def synthesize(req: dict) -> dict:
        config = _read_gradium_provider_config(req.get("providerConfig", {}))
        overrides = req.get("providerOverrides") or {}
        api_key = config["apiKey"] or os.environ.get("GRADIUM_API_KEY")
        if not api_key:
            raise RuntimeError("Gradium API key missing")
        wants_voice_note = req.get("target") == "voice-note"
        output_format = "opus" if wants_voice_note else "wav"
        audio_buffer = await gradium_tts(
            text=req["text"],
            api_key=api_key,
            baseUrl=config["baseUrl"],
            voiceId=_trim_to_undefined(overrides.get("voiceId")) or config["voiceId"],
            output_format=output_format,
            timeout_ms=req["timeoutMs"],
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "fileExtension": ".opus" if wants_voice_note else ".wav",
            "voiceCompatible": wants_voice_note,
        }

    async def synthesize_telephony(req: dict) -> dict:
        config = _read_gradium_provider_config(req.get("providerConfig", {}))
        overrides = req.get("providerOverrides") or {}
        api_key = config["apiKey"] or os.environ.get("GRADIUM_API_KEY")
        if not api_key:
            raise RuntimeError("Gradium API key missing")
        output_format = "ulaw_8000"
        sample_rate = 8000
        audio_buffer = await gradium_tts(
            text=req["text"],
            api_key=api_key,
            baseUrl=config["baseUrl"],
            voiceId=_trim_to_undefined(overrides.get("voiceId")) or config["voiceId"],
            output_format=output_format,
            timeout_ms=req["timeoutMs"],
            max_bytes=_resolve_generated_audio_max_bytes(req),
        )
        return {"audioBuffer": audio_buffer, "outputFormat": output_format, "sampleRate": sample_rate}

    return {
        "id": "gradium",
        "label": "Gradium",
        "autoSelectOrder": 30,
        "voices": [v["id"] for v in GRADIUM_VOICES],
        "resolveConfig": lambda ctx: _normalize_gradium_provider_config(ctx["rawConfig"]),
        "parseDirectiveToken": _parse_directive_token,
        "listVoices": list_voices,
        "isConfigured": is_configured,
        "synthesize": synthesize,
        "synthesizeTelephony": synthesize_telephony,
    }
