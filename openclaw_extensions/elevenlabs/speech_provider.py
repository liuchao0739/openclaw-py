"""Elevenlabs provider module implements model/runtime integration."""

from __future__ import annotations

import json
import math
import os
from typing import Any

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import (
    as_finite_number,
    as_record,
    normalize_lowercase_string_or_empty,
    normalize_optional_lowercase_string,
    normalize_optional_string,
    parse_strict_finite_number,
    parse_strict_integer,
)
from openclaw_extensions.elevenlabs.config_api import resolve_eleven_labs_api_key_with_profile_fallback
from openclaw_extensions.elevenlabs.shared import (
    is_valid_elevenlabs_voice_id,
    normalize_elevenlabs_base_url,
)
from openclaw_extensions.elevenlabs.tts import (
    _assert_ok_or_throw_provider_error,
    _default_fetch_fn,
    _fetch_with_ssrf_guard,
    _normalize_apply_text_normalization,
    _normalize_language_code,
    _normalize_seed,
    _read_provider_binary_response,
    _require_in_range,
    _ssrf_policy_from_http_base_url_allowed_hostname,
    eleven_labs_tts,
    eleven_labs_tts_stream,
)

DEFAULT_ELEVENLABS_VOICE_ID = "pMsXgVXv3BLzUgSXRplE"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_ELEVENLABS_VOICE_SETTINGS = {
    "stability": 0.5,
    "similarityBoost": 0.75,
    "style": 0,
    "useSpeakerBoost": True,
    "speed": 1,
}

ELEVENLABS_TTS_MODELS = (
    "eleven_v3",
    "eleven_multilingual_v2",
    "eleven_flash_v2_5",
    "eleven_flash_v2",
    "eleven_turbo_v2_5",
    "eleven_monolingual_v1",
)


def _normalize_elevenlabs_tts_model_id(value: str | None) -> str | None:
    if value == "eleven_turbo_v2_5":
        return "eleven_flash_v2_5"
    if value == "eleven_turbo_v2":
        return "eleven_flash_v2"
    return value


def _parse_boolean_value(value: str) -> bool | None:
    normalized = normalize_lowercase_string_or_empty(value)
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return None


def _parse_number_value(value: str) -> float | None:
    return parse_strict_finite_number(value)


def _as_boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _parse_boolean_value(value)
    return None


def _normalize_voice_setting(value: Any, min_value: float, max_value: float) -> float | None:
    number = as_finite_number(value)
    if number is None or number < min_value or number > max_value:
        return None
    return number


def _normalize_elevenlabs_seed(value: Any) -> int | None:
    seed = as_finite_number(value)
    if seed is None or not float(seed).is_integer() or seed < 0 or seed > 4_294_967_295:
        return None
    return int(seed)


def _normalize_elevenlabs_latency_tier(value: Any) -> int | None:
    latency_tier = as_finite_number(value)
    if latency_tier is None or not float(latency_tier).is_integer() or latency_tier < 0 or latency_tier > 4:
        return None
    return int(latency_tier)


def _normalize_voice_settings(
    raw_voice_settings: dict[str, Any] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if raw_voice_settings is None:
        return result
    stability = _normalize_voice_setting(raw_voice_settings.get("stability"), 0, 1)
    if stability is not None:
        result["stability"] = stability
    similarity_boost = _normalize_voice_setting(raw_voice_settings.get("similarityBoost"), 0, 1)
    if similarity_boost is not None:
        result["similarityBoost"] = similarity_boost
    style = _normalize_voice_setting(raw_voice_settings.get("style"), 0, 1)
    if style is not None:
        result["style"] = style
    use_speaker_boost = _as_boolean(raw_voice_settings.get("useSpeakerBoost"))
    if use_speaker_boost is not None:
        result["useSpeakerBoost"] = use_speaker_boost
    speed = _normalize_voice_setting(raw_voice_settings.get("speed"), 0.5, 2)
    if speed is not None:
        result["speed"] = speed
    return result


def _normalize_elevenlabs_provider_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    providers = as_record(raw_config.get("providers"))
    raw = as_record(providers.get("elevenlabs") if providers else None) or as_record(
        raw_config.get("elevenlabs")
    )
    raw_voice_settings = as_record(raw.get("voiceSettings") if raw else None)
    return {
        "apiKey": normalize_secret_input_string(raw.get("apiKey") if raw else None),
        "baseUrl": normalize_elevenlabs_base_url(normalize_optional_string(raw.get("baseUrl") if raw else None)),
        "voiceId": normalize_optional_string(raw.get("voiceId") if raw else None) or DEFAULT_ELEVENLABS_VOICE_ID,
        "modelId": _normalize_elevenlabs_tts_model_id(
            normalize_optional_string(raw.get("modelId") if raw else None)
        )
        or DEFAULT_ELEVENLABS_MODEL_ID,
        "seed": _normalize_elevenlabs_seed(raw.get("seed") if raw else None),
        "applyTextNormalization": normalize_optional_string(
            raw.get("applyTextNormalization") if raw else None
        ),
        "languageCode": normalize_optional_string(raw.get("languageCode") if raw else None),
        "voiceSettings": {
            **DEFAULT_ELEVENLABS_VOICE_SETTINGS,
            **_normalize_voice_settings(raw_voice_settings),
        },
    }


def _read_elevenlabs_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    defaults = _normalize_elevenlabs_provider_config({})
    voice_settings = as_record(config.get("voiceSettings"))
    return {
        "apiKey": normalize_optional_string(config.get("apiKey")) or defaults["apiKey"],
        "baseUrl": normalize_elevenlabs_base_url(
            normalize_optional_string(config.get("baseUrl")) or defaults["baseUrl"]
        ),
        "voiceId": normalize_optional_string(config.get("voiceId")) or defaults["voiceId"],
        "modelId": _normalize_elevenlabs_tts_model_id(
            normalize_optional_string(config.get("modelId"))
        )
        or defaults["modelId"],
        "seed": _normalize_elevenlabs_seed(config.get("seed")) or defaults["seed"],
        "applyTextNormalization": normalize_optional_string(config.get("applyTextNormalization"))
        or defaults["applyTextNormalization"],
        "languageCode": normalize_optional_string(config.get("languageCode")) or defaults["languageCode"],
        "voiceSettings": {
            **defaults["voiceSettings"],
            **_normalize_voice_settings(voice_settings),
        },
    }


def _merge_voice_settings_override(ctx: dict[str, Any], next_settings: dict[str, Any]) -> dict[str, Any]:
    current_overrides = ctx.get("currentOverrides")
    overrides = dict(current_overrides) if isinstance(current_overrides, dict) else {}
    existing_voice_settings = as_record(overrides.get("voiceSettings")) or {}
    overrides["voiceSettings"] = {**existing_voice_settings, **next_settings}
    return overrides


def _resolve_voice_settings_override(
    base: dict[str, Any],
    overrides: Any,
) -> dict[str, Any]:
    voice_settings = as_record(overrides)
    return {
        **base,
        **_normalize_voice_settings(voice_settings),
    }


def _parse_directive_token(ctx: dict[str, Any]) -> dict[str, Any]:
    try:
        key = str(ctx.get("key") or "").lower()
        policy = ctx.get("policy") if isinstance(ctx.get("policy"), dict) else {}
        current_overrides = ctx.get("currentOverrides")
        overrides = dict(current_overrides) if isinstance(current_overrides, dict) else {}
        value = ctx.get("value")

        if key in {"voiceid", "voice_id", "elevenlabs_voice", "elevenlabsvoice"}:
            if not policy.get("allowVoice"):
                return {"handled": True}
            if not is_valid_elevenlabs_voice_id(str(value or "")):
                return {"handled": True, "warnings": [f'invalid ElevenLabs voiceId "{value}"']}
            return {"handled": True, "overrides": {**overrides, "voiceId": value}}

        if key in {"model", "modelid", "model_id", "elevenlabs_model", "elevenlabsmodel"}:
            if not policy.get("allowModelId"):
                return {"handled": True}
            return {
                "handled": True,
                "overrides": {**overrides, "modelId": _normalize_elevenlabs_tts_model_id(str(value or ""))},
            }

        if key == "stability":
            if not policy.get("allowVoiceSettings"):
                return {"handled": True}
            parsed = _parse_number_value(str(value or ""))
            if parsed is None:
                return {"handled": True, "warnings": ["invalid stability value"]}
            _require_in_range(parsed, 0, 1, "stability")
            return {
                "handled": True,
                "overrides": _merge_voice_settings_override(ctx, {"stability": parsed}),
            }

        if key in {"similarity", "similarityboost", "similarity_boost"}:
            if not policy.get("allowVoiceSettings"):
                return {"handled": True}
            parsed = _parse_number_value(str(value or ""))
            if parsed is None:
                return {"handled": True, "warnings": ["invalid similarityBoost value"]}
            _require_in_range(parsed, 0, 1, "similarityBoost")
            return {
                "handled": True,
                "overrides": _merge_voice_settings_override(ctx, {"similarityBoost": parsed}),
            }

        if key == "style":
            if not policy.get("allowVoiceSettings"):
                return {"handled": True}
            parsed = _parse_number_value(str(value or ""))
            if parsed is None:
                return {"handled": True, "warnings": ["invalid style value"]}
            _require_in_range(parsed, 0, 1, "style")
            return {
                "handled": True,
                "overrides": _merge_voice_settings_override(ctx, {"style": parsed}),
            }

        if key == "speed":
            if not policy.get("allowVoiceSettings"):
                return {"handled": True}
            parsed = _parse_number_value(str(value or ""))
            if parsed is None:
                return {"handled": True, "warnings": ["invalid speed value"]}
            _require_in_range(parsed, 0.5, 2, "speed")
            return {
                "handled": True,
                "overrides": _merge_voice_settings_override(ctx, {"speed": parsed}),
            }

        if key in {"speakerboost", "speaker_boost", "usespeakerboost", "use_speaker_boost"}:
            if not policy.get("allowVoiceSettings"):
                return {"handled": True}
            parsed = _parse_boolean_value(str(value or ""))
            if parsed is None:
                return {"handled": True, "warnings": ["invalid useSpeakerBoost value"]}
            return {
                "handled": True,
                "overrides": _merge_voice_settings_override(ctx, {"useSpeakerBoost": parsed}),
            }

        if key in {"normalize", "applytextnormalization", "apply_text_normalization"}:
            if not policy.get("allowNormalization"):
                return {"handled": True}
            return {
                "handled": True,
                "overrides": {
                    **overrides,
                    "applyTextNormalization": _normalize_apply_text_normalization(str(value or "")),
                },
            }

        if key in {"language", "languagecode", "language_code"}:
            if not policy.get("allowNormalization"):
                return {"handled": True}
            return {
                "handled": True,
                "overrides": {
                    **overrides,
                    "languageCode": _normalize_language_code(str(value or "")),
                },
            }

        if key == "seed":
            if not policy.get("allowSeed"):
                return {"handled": True}
            parsed_seed = parse_strict_integer(str(value or ""))
            return {
                "handled": True,
                "overrides": {
                    **overrides,
                    "seed": _normalize_seed(parsed_seed if parsed_seed is not None else math.nan),
                },
            }

        return {"handled": False}
    except Exception as error:  # noqa: BLE001
        return {"handled": True, "warnings": [str(error)]}


async def _read_provider_json_response(response: Any, label: str) -> Any:
    raw = await _read_provider_binary_response(response, label, "JSON")
    return json.loads(raw.decode("utf-8"))


async def _list_elevenlabs_voices(*, api_key: str, base_url: str | None = None) -> list[dict[str, Any]]:
    normalized_base_url = normalize_elevenlabs_base_url(base_url)
    guarded = await _fetch_with_ssrf_guard(
        url=f"{normalized_base_url}/v1/voices",
        init={"headers": {"xi-api-key": api_key}},
        timeout_ms=60_000,
        policy=_ssrf_policy_from_http_base_url_allowed_hostname(normalized_base_url),
        audit_context="elevenlabs.voices",
    )
    response = guarded["response"]
    release = guarded["release"]
    try:
        await _assert_ok_or_throw_provider_error(response, "ElevenLabs voices API error")
        payload = await _read_provider_json_response(response, "elevenlabs.voices")
        voices = payload.get("voices") if isinstance(payload, dict) else None
        if not isinstance(voices, list):
            return []
        result: list[dict[str, Any]] = []
        for voice in voices:
            if not isinstance(voice, dict):
                continue
            voice_id = normalize_optional_string(voice.get("voice_id")) or ""
            if not voice_id:
                continue
            entry: dict[str, Any] = {"id": voice_id}
            name = normalize_optional_string(voice.get("name"))
            category = normalize_optional_string(voice.get("category"))
            description = normalize_optional_string(voice.get("description"))
            if name:
                entry["name"] = name
            if category:
                entry["category"] = category
            if description:
                entry["description"] = description
            result.append(entry)
        return result
    finally:
        await release()


def _resolve_elevenlabs_tts_request(
    req: dict[str, Any],
    *,
    output_format: str,
    latency_tier: int | None = None,
) -> dict[str, Any]:
    config = _read_elevenlabs_provider_config(
        req.get("providerConfig") if isinstance(req.get("providerConfig"), dict) else {}
    )
    overrides = req.get("providerOverrides")
    provider_overrides = overrides if isinstance(overrides, dict) else {}
    api_key = (
        config.get("apiKey")
        or resolve_eleven_labs_api_key_with_profile_fallback()
        or os.environ.get("XI_API_KEY")
    )
    if not api_key:
        raise RuntimeError("ElevenLabs API key missing")
    return {
        "text": str(req.get("text") or ""),
        "apiKey": api_key,
        "baseUrl": config["baseUrl"],
        "voiceId": normalize_optional_string(provider_overrides.get("voiceId")) or config["voiceId"],
        "modelId": _normalize_elevenlabs_tts_model_id(
            normalize_optional_string(provider_overrides.get("modelId"))
        )
        or config["modelId"],
        "outputFormat": output_format,
        "seed": _normalize_elevenlabs_seed(provider_overrides.get("seed")) or config.get("seed"),
        "applyTextNormalization": normalize_optional_string(
            provider_overrides.get("applyTextNormalization")
        )
        or config.get("applyTextNormalization"),
        "languageCode": normalize_optional_string(provider_overrides.get("languageCode"))
        or config.get("languageCode"),
        "latencyTier": latency_tier,
        "voiceSettings": _resolve_voice_settings_override(
            config["voiceSettings"],
            provider_overrides.get("voiceSettings"),
        ),
        "timeoutMs": int(req.get("timeoutMs") or 0),
    }


def build_eleven_labs_speech_provider() -> dict[str, Any]:
    async def list_voices(req: dict[str, Any]) -> list[dict[str, Any]]:
        provider_config = req.get("providerConfig")
        config = (
            _read_elevenlabs_provider_config(provider_config)
            if isinstance(provider_config, dict)
            else None
        )
        api_key = (
            req.get("apiKey")
            or (config.get("apiKey") if config else None)
            or resolve_eleven_labs_api_key_with_profile_fallback()
            or os.environ.get("XI_API_KEY")
        )
        if not api_key:
            raise RuntimeError("ElevenLabs API key missing")
        return await _list_elevenlabs_voices(
            api_key=api_key,
            base_url=req.get("baseUrl") or (config.get("baseUrl") if config else None),
        )

    def is_configured(params: dict[str, Any]) -> bool:
        provider_config = params.get("providerConfig")
        config = _read_elevenlabs_provider_config(
            provider_config if isinstance(provider_config, dict) else {}
        )
        return bool(
            config.get("apiKey")
            or resolve_eleven_labs_api_key_with_profile_fallback()
            or os.environ.get("XI_API_KEY")
        )

    async def synthesize(req: dict[str, Any]) -> dict[str, Any]:
        overrides = req.get("providerOverrides")
        provider_overrides = overrides if isinstance(overrides, dict) else {}
        output_format = normalize_optional_string(provider_overrides.get("outputFormat")) or (
            "opus_48000_64" if req.get("target") == "voice-note" else "mp3_44100_128"
        )
        audio_buffer = await eleven_labs_tts(
            **_resolve_elevenlabs_tts_request(
                req,
                output_format=output_format,
                latency_tier=_normalize_elevenlabs_latency_tier(provider_overrides.get("latencyTier")),
            )
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "fileExtension": ".opus" if req.get("target") == "voice-note" else ".mp3",
            "voiceCompatible": req.get("target") == "voice-note",
        }

    async def stream_synthesize(req: dict[str, Any]) -> dict[str, Any]:
        overrides = req.get("providerOverrides")
        provider_overrides = overrides if isinstance(overrides, dict) else {}
        output_format = normalize_optional_string(provider_overrides.get("outputFormat")) or (
            "opus_48000_64" if req.get("target") == "voice-note" else "mp3_44100_128"
        )
        stream = await eleven_labs_tts_stream(
            **_resolve_elevenlabs_tts_request(
                req,
                output_format=output_format,
                latency_tier=_normalize_elevenlabs_latency_tier(provider_overrides.get("latencyTier")),
            )
        )
        return {
            "audioStream": stream["audioStream"],
            "outputFormat": output_format,
            "fileExtension": ".opus" if req.get("target") == "voice-note" else ".mp3",
            "voiceCompatible": req.get("target") == "voice-note",
            "release": stream["release"],
        }

    async def synthesize_telephony(req: dict[str, Any]) -> dict[str, Any]:
        output_format = "pcm_22050"
        sample_rate = 22_050
        audio_buffer = await eleven_labs_tts(
            **_resolve_elevenlabs_tts_request(req, output_format=output_format)
        )
        return {
            "audioBuffer": audio_buffer,
            "outputFormat": output_format,
            "sampleRate": sample_rate,
        }

    def resolve_talk_config(params: dict[str, Any]) -> dict[str, Any]:
        base_tts_config = params.get("baseTtsConfig")
        talk_provider_config = params.get("talkProviderConfig")
        base = _normalize_elevenlabs_provider_config(
            base_tts_config if isinstance(base_tts_config, dict) else {}
        )
        talk = talk_provider_config if isinstance(talk_provider_config, dict) else {}
        talk_voice_settings = as_record(talk.get("voiceSettings"))
        resolved_talk_api_key = (
            resolve_eleven_labs_api_key_with_profile_fallback()
            if talk.get("apiKey") is None
            else normalize_secret_input_string(talk.get("apiKey"))
        )
        result = dict(base)
        if resolved_talk_api_key is not None:
            result["apiKey"] = resolved_talk_api_key
        talk_base_url = normalize_optional_string(talk.get("baseUrl"))
        if talk_base_url:
            result["baseUrl"] = normalize_elevenlabs_base_url(talk_base_url)
        talk_voice_id = normalize_optional_string(talk.get("voiceId"))
        if talk_voice_id:
            result["voiceId"] = talk_voice_id
        talk_model_id = normalize_optional_string(talk.get("modelId"))
        if talk_model_id:
            result["modelId"] = _normalize_elevenlabs_tts_model_id(talk_model_id)
        talk_seed = _normalize_elevenlabs_seed(talk.get("seed"))
        if talk_seed is not None:
            result["seed"] = talk_seed
        talk_normalization = normalize_optional_string(talk.get("applyTextNormalization"))
        if talk_normalization:
            result["applyTextNormalization"] = _normalize_apply_text_normalization(talk_normalization)
        talk_language = normalize_optional_string(talk.get("languageCode"))
        if talk_language:
            result["languageCode"] = _normalize_language_code(talk_language)
        result["voiceSettings"] = {
            **base["voiceSettings"],
            **_normalize_voice_settings(talk_voice_settings),
        }
        return result

    def resolve_talk_overrides(params: dict[str, Any]) -> dict[str, Any]:
        normalize = normalize_optional_string(params.get("normalize"))
        language = normalize_lowercase_string_or_empty(normalize_optional_string(params.get("language")))
        latency_tier = _normalize_elevenlabs_latency_tier(params.get("latencyTier"))
        voice_settings = {
            **(
                {"speed": speed}
                if (speed := _normalize_voice_setting(params.get("speed"), 0.5, 2)) is not None
                else {}
            ),
            **(
                {"stability": stability}
                if (stability := _normalize_voice_setting(params.get("stability"), 0, 1)) is not None
                else {}
            ),
            **(
                {"similarityBoost": similarity}
                if (similarity := _normalize_voice_setting(params.get("similarity"), 0, 1)) is not None
                else {}
            ),
            **(
                {"style": style}
                if (style := _normalize_voice_setting(params.get("style"), 0, 1)) is not None
                else {}
            ),
            **(
                {"useSpeakerBoost": speaker_boost}
                if (speaker_boost := _as_boolean(params.get("speakerBoost"))) is not None
                else {}
            ),
        }
        result: dict[str, Any] = {}
        voice_id = normalize_optional_string(params.get("voiceId"))
        if voice_id:
            result["voiceId"] = voice_id
        model_id = normalize_optional_string(params.get("modelId"))
        if model_id:
            result["modelId"] = _normalize_elevenlabs_tts_model_id(model_id)
        output_format = normalize_optional_string(params.get("outputFormat"))
        if output_format:
            result["outputFormat"] = output_format
        seed = _normalize_elevenlabs_seed(params.get("seed"))
        if seed is not None:
            result["seed"] = seed
        if normalize:
            result["applyTextNormalization"] = _normalize_apply_text_normalization(normalize)
        if language:
            result["languageCode"] = _normalize_language_code(language)
        if latency_tier is not None:
            result["latencyTier"] = latency_tier
        if voice_settings:
            result["voiceSettings"] = voice_settings
        return result

    return {
        "id": "elevenlabs",
        "label": "ElevenLabs",
        "autoSelectOrder": 20,
        "defaultModel": DEFAULT_ELEVENLABS_MODEL_ID,
        "models": list(ELEVENLABS_TTS_MODELS),
        "resolveConfig": lambda params: _normalize_elevenlabs_provider_config(
            params.get("rawConfig") if isinstance(params.get("rawConfig"), dict) else {}
        ),
        "parseDirectiveToken": _parse_directive_token,
        "resolveTalkConfig": resolve_talk_config,
        "resolveTalkOverrides": resolve_talk_overrides,
        "listVoices": list_voices,
        "isConfigured": is_configured,
        "synthesize": synthesize,
        "streamSynthesize": stream_synthesize,
        "synthesizeTelephony": synthesize_telephony,
    }
