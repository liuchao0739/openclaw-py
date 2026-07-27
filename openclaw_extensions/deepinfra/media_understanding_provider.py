from typing import Dict, List, Optional, Any

from .media_models import DEEPINFRA_VLM_FALLBACK_MODELS, normalize_deepinfra_base_url, normalize_deepinfra_model_ref
from .provider_models import DEEPINFRA_BASE_URL, DeepInfraSurfaceModel
from .surface_model_catalogs import resolve_deepinfra_vlm_model_capabilities


def build_deepinfra_media_understanding_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    vlm_models = options.get("vlmModels", [])

    ids = [m.id for m in vlm_models] if vlm_models else list(DEEPINFRA_VLM_FALLBACK_MODELS)
    default_model = ids[0] if ids else DEEPINFRA_VLM_FALLBACK_MODELS[0]

    return {
        "id": "deepinfra",
        "label": "DeepInfra",
        "autoPriority": {"image": 45, "audio": 45},
        "capabilities": {
            "image": {
                "enabled": True,
                "modelRequired": True,
                "supportsMultiImage": True,
                "maxImages": 16,
            },
            "audio": {
                "enabled": True,
                "modelRequired": True,
                "supportsMultiAudio": False,
                "maxAudio": 1,
            },
        },
        "defaultModels": {"image": default_model, "audio": default_model},
        "models": ids,
        "resolveModelCapabilities": resolve_deepinfra_vlm_model_capabilities,
        "resolveBaseUrl": lambda ctx: normalize_deepinfra_base_url(
            ctx.get("providerConfig", {}).get("baseUrl"), DEEPINFRA_BASE_URL
        ),
        "normalizeModel": lambda model: normalize_deepinfra_model_ref(model, default_model),
        "buildImageRequest": lambda ctx: {
            "model": ctx.get("model"),
            "messages": ctx.get("messages"),
            "max_tokens": ctx.get("maxTokens") or 4096,
        },
        "buildAudioRequest": lambda ctx: {
            "model": ctx.get("model"),
            "messages": ctx.get("messages"),
            "max_tokens": ctx.get("maxTokens") or 4096,
        },
        "response": {"streamed": True},
        "apiErrorLabel": "DeepInfra media understanding API error",
        "missingApiKeyError": "DeepInfra API key missing",
    }

__all__ = ["build_deepinfra_media_understanding_provider"]