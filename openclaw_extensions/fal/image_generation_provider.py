import json
import re
from typing import Dict, List, Optional, Any

from .http_config import FAL_BASE_URL, resolve_fal_http_request_config


DEFAULT_FAL_IMAGE_MODEL = "fal-ai/flux/dev"
DEFAULT_FAL_EDIT_SUBPATH = "image-to-image"
FAL_KREA_2_MODEL_PREFIX = "krea/v2/"
FAL_KREA_2_MEDIUM_MODEL = "krea/v2/medium/text-to-image"
FAL_KREA_2_LARGE_MODEL = "krea/v2/large/text-to-image"
DEFAULT_OUTPUT_FORMAT = "png"
GPT_IMAGE_EDIT_MAX_INPUT_IMAGES = 10
NANO_BANANA_EDIT_MAX_INPUT_IMAGES = 14
KREA_STYLE_REFERENCE_MAX_INPUT_IMAGES = 10

FAL_OUTPUT_FORMATS = ["png", "jpeg"]
FAL_SUPPORTED_SIZES = ["1024x1024", "1024x1536", "1536x1024", "1024x1792", "1792x1024"]
FAL_SUPPORTED_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "2.35:1", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9", "4:1", "1:4", "8:1", "1:8"
]
KREA_SUPPORTED_ASPECT_RATIOS = ["1:1", "4:3", "3:2", "16:9", "2.35:1", "4:5", "2:3", "9:16"]
NANO_BANANA_SUPPORTED_ASPECT_RATIOS = [
    "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4",
    "2:3", "9:16", "4:1", "1:4", "8:1", "1:8"
]
KREA_CREATIVITY_LEVELS = ["raw", "low", "medium", "high"]

FAL_IMAGE_MALFORMED_RESPONSE = "fal image generation response malformed"
DEFAULT_GENERATED_IMAGE_MAX_BYTES = 6 * 1024 * 1024


def normalize_lowercase_string_or_empty(value: Optional[str]) -> str:
    return value.strip().lower() if value else ""


def normalize_optional_string(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def is_record(value: Any) -> bool:
    return isinstance(value, dict)


def parse_size(raw: Optional[str]) -> Optional[Dict[str, int]]:
    trimmed = raw.strip() if raw else None
    if not trimmed:
        return None
    match = re.match(r"^(\d{2,5})x(\d{2,5})$", trimmed, re.IGNORECASE)
    if not match:
        return None
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        return None
    return {"width": width, "height": height}


def parse_aspect_ratio_parts(aspect_ratio: str) -> Dict[str, float]:
    match = re.match(r"^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$", aspect_ratio.strip())
    if not match:
        raise ValueError(f"Invalid fal aspect ratio: {aspect_ratio}")
    width_ratio = float(match.group(1))
    height_ratio = float(match.group(2))
    if width_ratio <= 0 or height_ratio <= 0:
        raise ValueError(f"Invalid fal aspect ratio: {aspect_ratio}")
    return {"widthRatio": width_ratio, "heightRatio": height_ratio}


def aspect_ratio_to_dimensions(aspect_ratio: str, edge: int) -> Dict[str, int]:
    parts = parse_aspect_ratio_parts(aspect_ratio)
    width_ratio, height_ratio = parts["widthRatio"], parts["heightRatio"]
    if width_ratio >= height_ratio:
        return {
            "width": edge,
            "height": max(1, round((edge * height_ratio) / width_ratio))
        }
    return {
        "width": max(1, round((edge * width_ratio) / height_ratio)),
        "height": edge
    }


def resolve_fal_image_model_schema(model: str) -> Dict:
    if model.startswith(FAL_KREA_2_MODEL_PREFIX):
        return {
            "geometry": "native_aspect_ratio",
            "aspectRatios": KREA_SUPPORTED_ASPECT_RATIOS,
            "referenceImages": "image_style_references",
            "maxInputImages": KREA_STYLE_REFERENCE_MAX_INPUT_IMAGES,
            "referenceLimitLabel": "fal Krea 2",
            "referenceLimitNoun": "style reference",
            "appendEditPath": False,
            "supportsCount": False,
            "supportsOutputFormat": False,
            "defaultBody": {"creativity": "medium"},
        }
    if model.startswith("openai/gpt-image-") or model.startswith("fal-ai/nano-banana-"):
        is_nano_banana = model.startswith("fal-ai/nano-banana-")
        return {
            "geometry": "native_aspect_ratio" if is_nano_banana else "image_size",
            **({"aspectRatios": NANO_BANANA_SUPPORTED_ASPECT_RATIOS} if is_nano_banana else {}),
            "referenceImages": "image_urls",
            "maxInputImages": NANO_BANANA_EDIT_MAX_INPUT_IMAGES if is_nano_banana else GPT_IMAGE_EDIT_MAX_INPUT_IMAGES,
            "referenceLimitLabel": "fal Nano Banana 2" if is_nano_banana else "fal GPT Image edit",
            "referenceLimitNoun": "reference image",
            "appendEditPath": "edit",
            "supportsCount": True,
            "supportsOutputFormat": True,
        }
    return {
        "geometry": "image_size",
        "referenceImages": "image_url",
        "maxInputImages": 1,
        "referenceLimitLabel": "fal flux image generation currently",
        "referenceLimitNoun": "reference image",
        "appendEditPath": "image-to-image",
        "supportsCount": True,
        "supportsOutputFormat": True,
    }


def ensure_fal_model_path(model: Optional[str], has_input_images: bool) -> str:
    trimmed = model.strip() if model else DEFAULT_FAL_IMAGE_MODEL
    schema = resolve_fal_image_model_schema(trimmed)
    if has_input_images and schema["appendEditPath"] is False:
        return trimmed
    if not has_input_images:
        return trimmed
    if trimmed.endswith("/edit") or trimmed.endswith(f"/{DEFAULT_FAL_EDIT_SUBPATH}") or "/image-to-image/" in trimmed:
        return trimmed
    if trimmed.startswith("openai/gpt-image-") or trimmed.startswith("fal-ai/nano-banana-"):
        return f"{trimmed}/edit"
    return f"{trimmed}/{DEFAULT_FAL_EDIT_SUBPATH}"


def build_fal_image_generation_provider() -> Dict:
    return {
        "id": "fal",
        "label": "fal",
        "defaultModel": DEFAULT_FAL_IMAGE_MODEL,
        "models": [
            DEFAULT_FAL_IMAGE_MODEL,
            f"{DEFAULT_FAL_IMAGE_MODEL}/{DEFAULT_FAL_EDIT_SUBPATH}",
            FAL_KREA_2_MEDIUM_MODEL,
            FAL_KREA_2_LARGE_MODEL,
        ],
        "capabilities": {
            "generate": {
                "maxCount": 4,
                "supportsSize": True,
                "supportsAspectRatio": True,
                "supportsResolution": True,
            },
            "edit": {
                "enabled": True,
                "maxCount": 4,
                "maxInputImages": GPT_IMAGE_EDIT_MAX_INPUT_IMAGES,
                "supportsSize": True,
                "supportsAspectRatio": True,
                "supportsResolution": True,
            },
            "geometry": {
                "sizes": FAL_SUPPORTED_SIZES[:],
                "sizesByModel": {
                    FAL_KREA_2_MEDIUM_MODEL: [],
                    FAL_KREA_2_LARGE_MODEL: [],
                },
                "aspectRatios": FAL_SUPPORTED_ASPECT_RATIOS[:],
                "resolutions": ["1K", "2K", "4K"],
            },
            "output": {
                "formats": FAL_OUTPUT_FORMATS[:],
            },
        },
        "generateImage": lambda req: {},
    }

__all__ = ["build_fal_image_generation_provider"]