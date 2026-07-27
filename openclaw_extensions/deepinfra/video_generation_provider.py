import urllib.parse
from typing import Dict, List, Optional, Any

from .media_models import (
    DEEPINFRA_NATIVE_BASE_URL,
    DEEPINFRA_VIDEO_ASPECT_RATIOS,
    DEEPINFRA_VIDEO_DURATIONS,
    DEEPINFRA_VIDEO_FALLBACK_MODELS,
    normalize_deepinfra_base_url,
    normalize_deepinfra_model_ref,
)
from .provider_models import DeepInfraSurfaceModel
from .surface_model_catalogs import resolve_deepinfra_video_model_capabilities


def encode_deepinfra_model_path(model: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in model.split("/"))


def normalize_deepinfra_video_url(url: str) -> str:
    if url.startswith(("http://", "https://", "data:")):
        return url
    return urllib.parse.urljoin("https://api.deepinfra.com", url)


def resolve_duration_seconds(value: Optional[float]) -> Optional[int]:
    if value is None or not isinstance(value, (int, float)):
        return None
    return 5 if value <= 6.5 else 8


def resolve_seed(value: Any) -> Optional[int]:
    if isinstance(value, int) and 0 <= value <= 4294967295:
        return value
    return None


def build_deepinfra_video_body(req: Dict[str, Any], model: str) -> Dict[str, Any]:
    options = req.get("providerOptions", {})
    body: Dict[str, Any] = {"prompt": req.get("prompt")}

    aspect_ratio = req.get("aspectRatio")
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio

    duration = resolve_duration_seconds(req.get("durationSeconds"))
    if duration:
        body["duration"] = duration

    seed = resolve_seed(options.get("seed"))
    if seed is not None:
        body["seed"] = seed

    negative_prompt = options.get("negative_prompt") or options.get("negativePrompt")
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    style = options.get("style")
    if style:
        body["style"] = style

    guidance_scale = options.get("guidance_scale") or options.get("guidanceScale")
    if guidance_scale is not None and model.startswith("Wan-AI/"):
        body["guidance_scale"] = guidance_scale

    return body


def build_deepinfra_video_generation_provider(options: Dict[str, any] = None) -> Dict[str, any]:
    options = options or {}
    video_gen_models = options.get("videoGenModels", [])

    ids = [m.id for m in video_gen_models] if video_gen_models else list(DEEPINFRA_VIDEO_FALLBACK_MODELS)
    default_model = ids[0] if ids else DEEPINFRA_VIDEO_FALLBACK_MODELS[0]

    return {
        "id": "deepinfra",
        "label": "DeepInfra",
        "defaultModel": default_model,
        "models": ids,
        "resolveModelCapabilities": resolve_deepinfra_video_model_capabilities,
        "isConfigured": lambda ctx: False,
        "capabilities": {
            "generate": {
                "maxVideos": 1,
                "maxDurationSeconds": 8,
                "supportedDurationSeconds": list(DEEPINFRA_VIDEO_DURATIONS),
                "supportsAspectRatio": True,
                "aspectRatios": list(DEEPINFRA_VIDEO_ASPECT_RATIOS),
                "providerOptions": {
                    "seed": "number",
                    "negative_prompt": "string",
                    "negativePrompt": "string",
                    "style": "string",
                    "guidance_scale": "number",
                    "guidanceScale": "number",
                },
            },
            "imageToVideo": {"enabled": False},
            "videoToVideo": {"enabled": False},
        },
        "generateVideo": lambda req: {},
    }

__all__ = ["build_deepinfra_video_generation_provider"]