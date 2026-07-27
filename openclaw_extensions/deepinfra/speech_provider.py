from typing import Dict, List, Optional

from .media_models import (
    DEFAULT_DEEPINFRA_TTS_VOICE,
    DEEPINFRA_TTS_FALLBACK_MODELS,
    normalize_deepinfra_model_ref,
)
from .provider_models import DEEPINFRA_BASE_URL, DeepInfraSurfaceModel


DEEPINFRA_TTS_RESPONSE_FORMATS = ["mp3", "opus", "flac", "wav", "pcm"]


def build_deepinfra_speech_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    tts_models = options.get("ttsModels", [])

    ids = [m.id for m in tts_models] if tts_models else list(DEEPINFRA_TTS_FALLBACK_MODELS)
    default_model = ids[0] if ids else DEEPINFRA_TTS_FALLBACK_MODELS[0]

    return {
        "id": "deepinfra",
        "label": "DeepInfra",
        "autoSelectOrder": 45,
        "models": ids,
        "voices": [DEFAULT_DEEPINFRA_TTS_VOICE],
        "defaultModel": default_model,
        "defaultVoice": DEFAULT_DEEPINFRA_TTS_VOICE,
        "defaultBaseUrl": DEEPINFRA_BASE_URL,
        "envKey": "DEEPINFRA_API_KEY",
        "responseFormats": list(DEEPINFRA_TTS_RESPONSE_FORMATS),
        "defaultResponseFormat": "mp3",
        "voiceCompatibleResponseFormats": ["mp3", "opus"],
        "baseUrlPolicy": {"kind": "trim-trailing-slash"},
        "normalizeModel": lambda model: normalize_deepinfra_model_ref(model, default_model),
        "apiErrorLabel": "DeepInfra TTS API error",
        "missingApiKeyError": "DeepInfra API key missing",
        "readExtraConfig": lambda raw: {"extraBody": raw.get("extraBody", {}) if raw else {}},
        "extraJsonBodyFields": [{"configKey": "extraBody", "requestKey": "extra_body"}],
    }

__all__ = ["build_deepinfra_speech_provider"]