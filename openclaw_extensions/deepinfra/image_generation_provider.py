from typing import Dict, List, Optional

from .media_models import (
    DEFAULT_DEEPINFRA_IMAGE_SIZE,
    DEEPINFRA_BASE_URL,
    DEEPINFRA_IMAGE_FALLBACK_MODELS,
    normalize_deepinfra_base_url,
    normalize_deepinfra_model_ref,
)
from .provider_models import DeepInfraSurfaceModel


DEEPINFRA_IMAGE_SIZES = ["512x512", "1024x1024", "1024x1792", "1792x1024"]
MAX_DEEPINFRA_INPUT_IMAGES = 1


def build_deepinfra_image_generation_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    image_gen_models = options.get("imageGenModels", [])

    ids = [m.id for m in image_gen_models] if image_gen_models else list(DEEPINFRA_IMAGE_FALLBACK_MODELS)
    default_model = ids[0] if ids else DEEPINFRA_IMAGE_FALLBACK_MODELS[0]

    return {
        "id": "deepinfra",
        "label": "DeepInfra",
        "defaultModel": default_model,
        "models": ids,
        "capabilities": {
            "generate": {
                "maxCount": 4,
                "supportsSize": True,
                "supportsAspectRatio": False,
                "supportsResolution": False,
            },
            "edit": {
                "enabled": True,
                "maxCount": 1,
                "maxInputImages": MAX_DEEPINFRA_INPUT_IMAGES,
                "supportsSize": True,
                "supportsAspectRatio": False,
                "supportsResolution": False,
            },
            "geometry": {
                "sizes": list(DEEPINFRA_IMAGE_SIZES),
            },
        },
        "defaultBaseUrl": DEEPINFRA_BASE_URL,
        "normalizeModel": lambda model: normalize_deepinfra_model_ref(model, default_model),
        "resolveBaseUrl": lambda ctx: normalize_deepinfra_base_url(
            ctx.get("providerConfig", {}).get("baseUrl"), DEEPINFRA_BASE_URL
        ),
        "resolveAllowPrivateNetwork": lambda: False,
        "useConfiguredRequest": True,
        "resolveCount": lambda ctx: 1 if ctx.get("mode") == "edit" else ctx.get("req", {}).get("count", 1),
        "buildGenerateRequest": lambda ctx: {
            "kind": "json",
            "body": {
                "model": ctx.get("model"),
                "prompt": ctx.get("req", {}).get("prompt"),
                "n": ctx.get("count"),
                "size": ctx.get("req", {}).get("size") or DEFAULT_DEEPINFRA_IMAGE_SIZE,
                "response_format": "b64_json",
            },
        },
        "buildEditRequest": lambda ctx: {
            "kind": "multipart",
            "form": {},
        },
        "response": {"defaultMimeType": "image/jpeg", "sniffMimeType": True},
        "tooManyInputImagesError": "DeepInfra image editing supports one reference image.",
        "missingApiKeyError": "DeepInfra API key missing",
        "emptyResponseError": "DeepInfra image response did not include generated image data",
        "failureLabels": {
            "generate": "DeepInfra image generation failed",
            "edit": "DeepInfra image edit failed",
        },
    }

__all__ = ["build_deepinfra_image_generation_provider"]