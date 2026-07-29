import os
from typing import Any, Optional

from .._sdk import normalize_secret_input
from .tts import (
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


def _as_object(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _trim_to_undefined(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _as_finite_number(value: Any) -> Optional[int]:
    if isinstance(value, (int, float)) and value == value:
        return int(value)
    return None


def _read_env_api_key() -> Optional[str]:
    return (
        _trim_to_undefined(os.environ.get("AZURE_SPEECH_KEY"))
        or _trim_to_undefined(os.environ.get("AZURE_SPEECH_API_KEY"))
        or _trim_to_undefined(os.environ.get("SPEECH_KEY"))
    )


def _read_env_region() -> Optional[str]:
    return (
        _trim_to_undefined(os.environ.get("AZURE_SPEECH_REGION"))
        or _trim_to_undefined(os.environ.get("SPEECH_REGION"))
    )


def _read_env_endpoint() -> Optional[str]:
    return _trim_to_undefined(os.environ.get("AZURE_SPEECH_ENDPOINT"))


def _resolve_config_record(raw_config: dict) -> dict:
    providers = _as_object(raw_config.get("providers"))
    return (
        _as_object(providers.get("azure-speech"))
        or _as_object(providers.get("azure"))
        or _as_object(raw_config.get("azure-speech"))
        or _as_object(raw_config.get("azure"))
    )


def _normalize_provider_config(raw_config: dict) -> dict:
    raw = _resolve_config_record(raw_config)
    region = _trim_to_undefined(raw.get("region")) or _read_env_region()
    endpoint = _trim_to_undefined(raw.get("endpoint")) or _read_env_endpoint()
    base_url = normalize_azure_speech_base_url({
        "baseUrl": _trim_to_undefined(raw.get("baseUrl")),
        "endpoint": endpoint,
        "region": region,
    })
    return {
        "apiKey": normalize_secret_input(raw.get("apiKey")),
        "region": region,
        "endpoint": endpoint,
        "baseUrl": base_url,
        "voice": _trim_to_undefined(raw.get("voice") or raw.get("voiceId")) or DEFAULT_AZURE_SPEECH_VOICE,
        "lang": _trim_to_undefined(raw.get("lang") or raw.get("languageCode")) or DEFAULT_AZURE_SPEECH_LANG,
        "outputFormat": _trim_to_undefined(raw.get("outputFormat")) or DEFAULT_AZURE_SPEECH_AUDIO_FORMAT,
        "voiceNoteOutputFormat": _trim_to_undefined(raw.get("voiceNoteOutputFormat")) or DEFAULT_AZURE_SPEECH_VOICE_NOTE_FORMAT,
        "timeoutMs": _as_finite_number(raw.get("timeoutMs")),
    }


def _read_provider_config(config: dict) -> dict:
    defaults = _normalize_provider_config({})
    region = _trim_to_undefined(config.get("region")) or defaults["region"]
    endpoint = _trim_to_undefined(config.get("endpoint")) or defaults["endpoint"]
    base_url = normalize_azure_speech_base_url({
        "baseUrl": _trim_to_undefined(config.get("baseUrl")) or defaults["baseUrl"],
        "endpoint": endpoint,
        "region": region,
    })
    return {
        "apiKey": _trim_to_undefined(config.get("apiKey")) or defaults["apiKey"],
        "region": region,
        "endpoint": endpoint,
        "baseUrl": base_url,
        "voice": _trim_to_undefined(config.get("voice") or config.get("voiceId")) or defaults["voice"],
        "lang": _trim_to_undefined(config.get("lang") or config.get("languageCode")) or defaults["lang"],
        "outputFormat": _trim_to_undefined(config.get("outputFormat")) or defaults["outputFormat"],
        "voiceNoteOutputFormat": _trim_to_undefined(config.get("voiceNoteOutputFormat")) or defaults["voiceNoteOutputFormat"],
        "timeoutMs": _as_finite_number(config.get("timeoutMs")) or defaults["timeoutMs"],
    }


def _read_overrides(overrides: Any) -> dict:
    if not overrides or not isinstance(overrides, dict):
        return {}
    return {
        "voice": _trim_to_undefined(overrides.get("voice") or overrides.get("voiceId")),
        "lang": _trim_to_undefined(overrides.get("lang") or overrides.get("languageCode")),
        "outputFormat": _trim_to_undefined(overrides.get("outputFormat")),
    }


def _parse_directive_token(ctx: dict) -> dict:
    key = ctx.get("key")
    voice_keys = {"voice", "voiceid", "voice_id", "azure_voice", "azurevoice", "azure_speech_voice"}
    lang_keys = {"lang", "language", "language_code", "languagecode", "azure_lang", "azure_language"}
    format_keys = {"output_format", "outputformat", "azure_format", "azure_output_format"}

    if key in voice_keys:
        if not ctx.get("policy", {}).get("allowVoice"):
            return {"handled": True}
        overrides = dict(ctx.get("currentOverrides", {}))
        overrides["voice"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}
    if key in lang_keys:
        if not ctx.get("policy", {}).get("allowVoiceSettings"):
            return {"handled": True}
        overrides = dict(ctx.get("currentOverrides", {}))
        overrides["lang"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}
    if key in format_keys:
        if not ctx.get("policy", {}).get("allowVoiceSettings"):
            return {"handled": True}
        overrides = dict(ctx.get("currentOverrides", {}))
        overrides["outputFormat"] = ctx.get("value")
        return {"handled": True, "overrides": overrides}
    return {"handled": False}


def _resolve_api_key(config: dict) -> Optional[str]:
    return config.get("apiKey") or _read_env_api_key()


def _resolve_timeout_ms(config: dict, timeout_ms: int) -> int:
    return config.get("timeoutMs") or timeout_ms


def _resolve_generated_audio_max_bytes(req: dict) -> int:
    configured = req.get("cfg", {}).get("agents", {}).get("defaults", {}).get("mediaMaxMb")
    if isinstance(configured, (int, float)) and configured == configured and configured > 0:
        return int(configured * 1024 * 1024)
    return DEFAULT_GENERATED_AUDIO_MAX_BYTES


def build_azure_speech_provider() -> dict:
    async def list_voices(req: dict) -> list:
        config = _read_provider_config(req["providerConfig"]) if req.get("providerConfig") else None
        api_key = req.get("apiKey") or (_resolve_api_key(config) if config else _read_env_api_key())
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        return await list_azure_speech_voices({
            "apiKey": api_key,
            "baseUrl": req.get("baseUrl") or (config.get("baseUrl") if config else None),
            "endpoint": config.get("endpoint") if config else None,
            "region": (config.get("region") if config else None) or _read_env_region(),
            "timeoutMs": config.get("timeoutMs") if config else None,
        })

    def is_configured(req: dict) -> bool:
        config = _read_provider_config(req.get("providerConfig", {}))
        return bool(_resolve_api_key(config) and (config.get("baseUrl") or config.get("region") or config.get("endpoint")))

    async def synthesize(req: dict) -> dict:
        config = _read_provider_config(req["providerConfig"])
        overrides = _read_overrides(req.get("providerOverrides"))
        api_key = _resolve_api_key(config)
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        output_format = (
            overrides.get("outputFormat")
            or (config["voiceNoteOutputFormat"] if req.get("target") == "voice-note" else config["outputFormat"])
        )
        audio_buffer = await azure_speech_tts({
            "text": req["text"],
            "apiKey": api_key,
            "baseUrl": config["baseUrl"],
            "endpoint": config["endpoint"],
            "region": config["region"],
            "voice": overrides.get("voice") or config["voice"],
            "lang": overrides.get("lang") or config["lang"],
            "outputFormat": output_format,
            "timeoutMs": _resolve_timeout_ms(config, req.get("timeoutMs", 30000)),
            "maxBytes": _resolve_generated_audio_max_bytes(req),
        })
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "fileExtension": infer_azure_speech_file_extension(output_format),
            "voiceCompatible": is_azure_speech_voice_compatible(output_format),
        }

    async def synthesize_telephony(req: dict) -> dict:
        config = _read_provider_config(req["providerConfig"])
        overrides = _read_overrides(req.get("providerOverrides"))
        api_key = _resolve_api_key(config)
        if not api_key:
            raise RuntimeError("Azure Speech API key missing")
        sample_rate = 8000
        audio_buffer = await azure_speech_tts({
            "text": req["text"],
            "apiKey": api_key,
            "baseUrl": config["baseUrl"],
            "endpoint": config["endpoint"],
            "region": config["region"],
            "voice": overrides.get("voice") or config["voice"],
            "lang": overrides.get("lang") or config["lang"],
            "outputFormat": DEFAULT_AZURE_SPEECH_TELEPHONY_FORMAT,
            "timeoutMs": _resolve_timeout_ms(config, req.get("timeoutMs", 30000)),
            "maxBytes": _resolve_generated_audio_max_bytes(req),
        })
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
        "resolveConfig": lambda ctx: _normalize_provider_config(ctx["rawConfig"]),
        "parseDirectiveToken": _parse_directive_token,
        "listVoices": list_voices,
        "isConfigured": is_configured,
        "synthesize": synthesize,
        "synthesizeTelephony": synthesize_telephony,
    }
