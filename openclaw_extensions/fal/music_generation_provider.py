from typing import Dict, List, Optional, Any

from .http_config import FAL_BASE_URL, resolve_fal_http_request_config


DEFAULT_FAL_MUSIC_MODEL = "fal-ai/minimax-music/v2.6"
FAL_ACE_STEP_MODEL = "fal-ai/ace-step/prompt-to-audio"
FAL_STABLE_AUDIO_MODEL = "fal-ai/stable-audio-25/text-to-audio"
DEFAULT_TIMEOUT_MS = 180_000
DEFAULT_GENERATED_MUSIC_MAX_BYTES = 16 * 1024 * 1024

FAL_MUSIC_MODELS = [DEFAULT_FAL_MUSIC_MODEL, FAL_ACE_STEP_MODEL, FAL_STABLE_AUDIO_MODEL]


def normalize_optional_string(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def build_fal_music_generation_provider() -> Dict:
    return {
        "id": "fal",
        "label": "fal",
        "defaultModel": DEFAULT_FAL_MUSIC_MODEL,
        "models": FAL_MUSIC_MODELS[:],
        "capabilities": {
            "generate": {
                "maxTracks": 1,
                "maxDurationSeconds": 240,
                "supportsLyrics": True,
                "supportsLyricsByModel": {
                    FAL_ACE_STEP_MODEL: False,
                    FAL_STABLE_AUDIO_MODEL: False,
                },
                "supportsInstrumental": True,
                "supportsInstrumentalByModel": {
                    FAL_STABLE_AUDIO_MODEL: False,
                },
                "supportsDuration": True,
                "supportsFormat": True,
                "supportedFormats": ["mp3", "wav"],
                "supportedFormatsByModel": {
                    DEFAULT_FAL_MUSIC_MODEL: ["mp3"],
                    FAL_ACE_STEP_MODEL: ["wav"],
                    FAL_STABLE_AUDIO_MODEL: ["wav"],
                },
            },
            "edit": {
                "enabled": False,
            },
        },
        "generateMusic": lambda req: {},
    }

__all__ = ["build_fal_music_generation_provider"]