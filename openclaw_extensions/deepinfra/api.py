import json
import os
from typing import Dict, List, Optional, Any

from .media_models import DEEPINFRA_NATIVE_BASE_URL
from .provider_models import DEEPINFRA_BASE_URL
from .provider_models import discover_deepinfra_models, discover_deepinfra_surfaces, DeepInfraSurfaceModel
from .image_generation_provider import build_deepinfra_image_generation_provider
from .speech_provider import build_deepinfra_speech_provider
from .video_generation_provider import build_deepinfra_video_generation_provider
from .media_understanding_provider import build_deepinfra_media_understanding_provider
from .embedding_provider import build_deepinfra_embedding_provider
from .memory_embedding_adapter import build_deepinfra_memory_embedding_provider
from .surface_model_catalogs import (
    get_deepinfra_image_gen_models,
    get_deepinfra_video_gen_models,
    get_deepinfra_tts_models,
    get_deepinfra_stt_models,
    get_deepinfra_embed_models,
    get_deepinfra_vlm_models,
)


async def get_deepinfra_models(options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    return await discover_deepinfra_models(options)


async def get_deepinfra_surfaces(options: Dict[str, Any] = None) -> Dict[str, Any]:
    catalog = await discover_deepinfra_surfaces(options)
    return {
        "chat": [m.id for m in catalog.chat],
        "vlm": [m.id for m in catalog.vlm],
        "embed": [m.id for m in catalog.embed],
        "image-gen": [m.id for m in catalog.image_gen],
        "video-gen": [m.id for m in catalog.video_gen],
        "tts": [m.id for m in catalog.tts],
        "stt": [m.id for m in catalog.stt],
    }


async def build_deepinfra_image_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    image_models = await get_deepinfra_image_gen_models(options)
    return build_deepinfra_image_generation_provider({**options, "imageGenModels": image_models})


async def build_deepinfra_speech_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    tts_models = await get_deepinfra_tts_models(options)
    return build_deepinfra_speech_provider({**options, "ttsModels": tts_models})


async def build_deepinfra_video_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    video_models = await get_deepinfra_video_gen_models(options)
    return build_deepinfra_video_generation_provider({**options, "videoGenModels": video_models})


async def build_deepinfra_media_understanding_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    vlm_models = await get_deepinfra_vlm_models(options)
    return build_deepinfra_media_understanding_provider({**options, "vlmModels": vlm_models})


async def build_deepinfra_embedding_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    embed_models = await get_deepinfra_embed_models(options)
    return build_deepinfra_embedding_provider({**options, "embedModels": embed_models})


async def build_deepinfra_memory_embedding_provider(options: Dict[str, Any] = None) -> Dict[str, Any]:
    embed_models = await get_deepinfra_embed_models(options)
    return build_deepinfra_memory_embedding_provider({**options, "embedModels": embed_models})

__all__ = [
    "DEEPINFRA_BASE_URL",
    "DEEPINFRA_NATIVE_BASE_URL",
    "get_deepinfra_models",
    "get_deepinfra_surfaces",
    "build_deepinfra_image_provider",
    "build_deepinfra_speech_provider",
    "build_deepinfra_video_provider",
    "build_deepinfra_media_understanding_provider",
    "build_deepinfra_embedding_provider",
    "build_deepinfra_memory_embedding_provider",
]