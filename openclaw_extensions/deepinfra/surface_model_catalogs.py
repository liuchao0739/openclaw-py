from typing import Dict, List, Optional, Any

from .media_models import DEEPINFRA_IMAGE_FALLBACK_MODELS, DEEPINFRA_VIDEO_FALLBACK_MODELS, DEEPINFRA_TTS_FALLBACK_MODELS, DEEPINFRA_STT_FALLBACK_MODELS, DEEPINFRA_EMBED_FALLBACK_MODELS, DEEPINFRA_VLM_FALLBACK_MODELS
from .provider_models import DeepInfraSurfaceModel, DeepInfraDiscoveredCatalog, discover_deepinfra_surfaces

DISCOVERY_CACHE: Optional[DeepInfraDiscoveredCatalog] = None
DISCOVERY_FETCH_IN_PROGRESS: bool = False


async def fetch_deepinfra_surface_catalog(options: Dict[str, Any] = None) -> DeepInfraDiscoveredCatalog:
    global DISCOVERY_CACHE, DISCOVERY_FETCH_IN_PROGRESS

    if DISCOVERY_CACHE:
        return DISCOVERY_CACHE

    if DISCOVERY_FETCH_IN_PROGRESS:
        from time import sleep
        for _ in range(10):
            sleep(0.1)
            if DISCOVERY_CACHE:
                return DISCOVERY_CACHE
        return await discover_deepinfra_surfaces(options)

    DISCOVERY_FETCH_IN_PROGRESS = True
    try:
        DISCOVERY_CACHE = await discover_deepinfra_surfaces(options)
        return DISCOVERY_CACHE
    finally:
        DISCOVERY_FETCH_IN_PROGRESS = False


async def get_deepinfra_image_gen_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.image_gen:
        return catalog.image_gen
    return []


async def get_deepinfra_video_gen_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.video_gen:
        return catalog.video_gen
    return []


async def get_deepinfra_tts_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.tts:
        return catalog.tts
    return []


async def get_deepinfra_stt_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.stt:
        return catalog.stt
    return []


async def get_deepinfra_embed_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.embed:
        return catalog.embed
    return []


async def get_deepinfra_vlm_models(options: Dict[str, Any] = None) -> List[DeepInfraSurfaceModel]:
    catalog = await fetch_deepinfra_surface_catalog(options)
    if catalog.vlm:
        return catalog.vlm
    return []


def resolve_deepinfra_image_model_capabilities(model: str) -> Dict[str, Any]:
    size_map: Dict[str, List[str]] = {
        "black-forest-labs/FLUX-1-schnell": ["512x512", "1024x1024"],
        "black-forest-labs/FLUX-1-dev": ["512x512", "1024x1024", "1024x1792", "1792x1024"],
        "Qwen/Qwen-Image-Max": ["512x512", "1024x1024"],
        "stabilityai/sdxl-turbo": ["512x512", "1024x1024"],
        "run-diffusion/Juggernaut-Lightning-Flux": ["512x512", "1024x1024"],
    }

    return {
        "supportsSize": True,
        "sizes": size_map.get(model, ["1024x1024"]),
        "supportsEdit": True,
        "maxInputImages": 1,
    }


def resolve_deepinfra_video_model_capabilities(model: str) -> Dict[str, Any]:
    supported_aspect_ratios: Dict[str, List[str]] = {
        "Pixverse/Pixverse-T2V": ["16:9", "4:3", "1:1", "3:4", "9:16"],
        "Pixverse/Pixverse-T2V-HD": ["16:9", "4:3", "1:1", "3:4", "9:16"],
        "Wan-AI/Wan2.6-T2V": ["16:9", "4:3", "1:1", "3:4", "9:16"],
        "google/veo-3.1-fast": ["16:9", "4:3", "1:1"],
    }

    supported_durations: Dict[str, List[int]] = {
        "Pixverse/Pixverse-T2V": [5, 8],
        "Pixverse/Pixverse-T2V-HD": [5, 8],
        "Wan-AI/Wan2.6-T2V": [5, 8],
        "google/veo-3.1-fast": [5, 8],
    }

    return {
        "supportsAspectRatio": True,
        "aspectRatios": supported_aspect_ratios.get(model, ["16:9", "4:3", "1:1"]),
        "maxDurationSeconds": 8,
        "supportedDurationSeconds": supported_durations.get(model, [5, 8]),
        "supportsImageToVideo": False,
        "supportsVideoToVideo": False,
        "supportsSeed": True,
        "supportsNegativePrompt": True,
        "supportsStyle": True,
        "supportsGuidanceScale": model.startswith("Wan-AI/"),
    }


def resolve_deepinfra_tts_model_capabilities(model: str) -> Dict[str, Any]:
    return {
        "supportsVoice": True,
        "voices": ["af_bella"],
        "responseFormats": ["mp3", "opus", "flac", "wav", "pcm"],
    }


def resolve_deepinfra_stt_model_capabilities(model: str) -> Dict[str, Any]:
    return {
        "supportsLanguage": True,
        "supportsTranscription": True,
        "supportsTranslation": True,
    }


def resolve_deepinfra_embed_model_capabilities(model: str) -> Dict[str, Any]:
    return {
        "maxInputTokens": 8192,
        "embeddingDimensions": 1024,
    }


def resolve_deepinfra_vlm_model_capabilities(model: str) -> Dict[str, Any]:
    return {
        "supportsImage": True,
        "supportsAudio": False,
        "maxInputImages": 16,
    }

__all__ = [
    "fetch_deepinfra_surface_catalog",
    "get_deepinfra_image_gen_models",
    "get_deepinfra_video_gen_models",
    "get_deepinfra_tts_models",
    "get_deepinfra_stt_models",
    "get_deepinfra_embed_models",
    "get_deepinfra_vlm_models",
    "resolve_deepinfra_image_model_capabilities",
    "resolve_deepinfra_video_model_capabilities",
    "resolve_deepinfra_tts_model_capabilities",
    "resolve_deepinfra_stt_model_capabilities",
    "resolve_deepinfra_embed_model_capabilities",
    "resolve_deepinfra_vlm_model_capabilities",
]