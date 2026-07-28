import json
from typing import Dict, List, Optional, Any

from .http_config import FAL_BASE_URL, FAL_QUEUE_BASE_URL, resolve_fal_http_request_config


DEFAULT_FAL_VIDEO_MODEL = "fal-ai/minimax/video-01-live"
HEYGEN_VIDEO_AGENT_MODEL = "fal-ai/heygen/v2/video-agent"
SEEDANCE_2_TEXT_IMAGE_VIDEO_MODELS = [
    "bytedance/seedance-2.0/fast/text-to-video",
    "bytedance/seedance-2.0/fast/image-to-video",
    "bytedance/seedance-2.0/text-to-video",
    "bytedance/seedance-2.0/image-to-video",
]
SEEDANCE_2_REFERENCE_VIDEO_MODELS = [
    "bytedance/seedance-2.0/fast/reference-to-video",
    "bytedance/seedance-2.0/reference-to-video",
]
SEEDANCE_2_VIDEO_MODELS = SEEDANCE_2_TEXT_IMAGE_VIDEO_MODELS + SEEDANCE_2_REFERENCE_VIDEO_MODELS
SEEDANCE_2_DURATION_SECONDS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
SEEDANCE_REFERENCE_MAX_IMAGES = 9
SEEDANCE_REFERENCE_MAX_VIDEOS = 3
SEEDANCE_REFERENCE_MAX_AUDIOS = 3
SEEDANCE_REFERENCE_MAX_FILES = 12

DEFAULT_HTTP_TIMEOUT_MS = 30_000
DEFAULT_OPERATION_TIMEOUT_MS = 1_200_000
DEFAULT_GENERATED_VIDEO_MAX_BYTES = 16 * 1024 * 1024
POLL_INTERVAL_MS = 5_000

FAL_VIDEO_PENDING_STATUSES = {"IN_QUEUE", "IN_PROGRESS", "PROCESSING", "QUEUED", "STARTED"}


def normalize_lowercase_string_or_empty(value: Optional[str]) -> str:
    return value.strip().lower() if value else ""


def normalize_optional_string(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def is_fal_seedance2_model(model: str) -> bool:
    return model in SEEDANCE_2_VIDEO_MODELS


def is_fal_seedance2_reference_model(model: str) -> bool:
    return model in SEEDANCE_2_REFERENCE_VIDEO_MODELS


def build_fal_video_generation_provider() -> Dict:
    return {
        "id": "fal",
        "label": "fal",
        "defaultModel": DEFAULT_FAL_VIDEO_MODEL,
        "models": [
            DEFAULT_FAL_VIDEO_MODEL,
            HEYGEN_VIDEO_AGENT_MODEL,
            *SEEDANCE_2_VIDEO_MODELS,
            "fal-ai/kling-video/v2.1/master/text-to-video",
            "fal-ai/wan/v2.2-a14b/text-to-video",
            "fal-ai/wan/v2.2-a14b/image-to-video",
        ],
        "capabilities": {
            "generate": {
                "maxVideos": 1,
                "supportedDurationSecondsByModel": {
                    model: SEEDANCE_2_DURATION_SECONDS[:] for model in SEEDANCE_2_VIDEO_MODELS
                },
                "supportsAspectRatio": True,
                "supportsResolution": True,
                "supportsSize": True,
                "supportsAudio": True,
            },
            "imageToVideo": {
                "enabled": True,
                "maxVideos": 1,
                "maxInputImages": 1,
                "maxInputImagesByModel": {
                    model: SEEDANCE_REFERENCE_MAX_IMAGES for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "maxInputAudiosByModel": {
                    model: SEEDANCE_REFERENCE_MAX_AUDIOS for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "supportedDurationSecondsByModel": {
                    model: SEEDANCE_2_DURATION_SECONDS[:] for model in SEEDANCE_2_VIDEO_MODELS
                },
                "supportsAspectRatio": True,
                "supportsResolution": True,
                "supportsSize": True,
                "supportsAudio": True,
            },
            "videoToVideo": {
                "enabled": True,
                "maxVideos": 1,
                "maxInputImages": 0,
                "maxInputImagesByModel": {
                    model: SEEDANCE_REFERENCE_MAX_IMAGES for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "maxInputVideos": 0,
                "maxInputVideosByModel": {
                    model: SEEDANCE_REFERENCE_MAX_VIDEOS for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "maxInputAudiosByModel": {
                    model: SEEDANCE_REFERENCE_MAX_AUDIOS for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "supportedDurationSecondsByModel": {
                    model: SEEDANCE_2_DURATION_SECONDS[:] for model in SEEDANCE_2_REFERENCE_VIDEO_MODELS
                },
                "supportsAspectRatio": True,
                "supportsResolution": True,
                "supportsSize": True,
                "supportsAudio": True,
            },
        },
        "generateVideo": lambda req: {},
    }

__all__ = ["build_fal_video_generation_provider"]