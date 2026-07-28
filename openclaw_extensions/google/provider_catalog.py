from typing import Dict, List, Optional, Any

from .model_id import (
    strip_google_provider_prefix,
    normalize_google_model_id,
    parse_google_model_id,
    is_google_model_id,
    infer_google_provider_from_model_id,
    GOOGLE_MODEL_ID_ALIASES,
)


GOOGLE_STATIC_CATALOG: Dict[str, Dict[str, Any]] = {
    "google/gemini-2.5-pro": {
        "id": "google/gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "provider": "google",
        "family": "gemini",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "supports": {
            "text": True,
            "image": True,
            "audio": True,
            "video": True,
            "reasoning": True,
            "thinking": True,
            "tool_use": True,
            "structured_output": True,
            "web_search": True,
            "code_execution": True,
        },
        "capabilities": {
            "reasoning_efforts": ["LOW", "MEDIUM", "HIGH"],
            "audio_input": True,
            "audio_output": True,
            "image_input": True,
            "image_output": False,
            "video_input": True,
            "video_output": False,
            "text_to_speech": True,
            "speech_to_text": False,
        },
    },
    "google/gemini-2.0-flash": {
        "id": "google/gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "family": "gemini",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "supports": {
            "text": True,
            "image": True,
            "audio": True,
            "video": True,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": True,
            "code_execution": True,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": True,
            "audio_output": True,
            "image_input": True,
            "image_output": False,
            "video_input": True,
            "video_output": False,
            "text_to_speech": True,
            "speech_to_text": False,
        },
    },
    "google/gemini-1.5-pro": {
        "id": "google/gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "google",
        "family": "gemini",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "supports": {
            "text": True,
            "image": True,
            "audio": True,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": True,
            "code_execution": False,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": True,
            "audio_output": True,
            "image_input": True,
            "image_output": False,
            "video_input": False,
            "video_output": False,
            "text_to_speech": True,
            "speech_to_text": False,
        },
    },
    "google/gemini-1.5-flash": {
        "id": "google/gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "provider": "google",
        "family": "gemini",
        "context_window": 1048576,
        "max_output_tokens": 8192,
        "supports": {
            "text": True,
            "image": True,
            "audio": True,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": True,
            "code_execution": False,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": True,
            "audio_output": True,
            "image_input": True,
            "image_output": False,
            "video_input": False,
            "video_output": False,
            "text_to_speech": True,
            "speech_to_text": False,
        },
    },
    "google/gemini-1.0-pro": {
        "id": "google/gemini-1.0-pro",
        "name": "Gemini 1.0 Pro",
        "provider": "google",
        "family": "gemini",
        "context_window": 30720,
        "max_output_tokens": 2048,
        "supports": {
            "text": True,
            "image": False,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": False,
            "code_execution": False,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": False,
            "audio_output": False,
            "image_input": False,
            "image_output": False,
            "video_input": False,
            "video_output": False,
            "text_to_speech": False,
            "speech_to_text": False,
        },
    },
    "google/gemini-1.0-flash": {
        "id": "google/gemini-1.0-flash",
        "name": "Gemini 1.0 Flash",
        "provider": "google",
        "family": "gemini",
        "context_window": 30720,
        "max_output_tokens": 2048,
        "supports": {
            "text": True,
            "image": False,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": False,
            "code_execution": False,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": False,
            "audio_output": False,
            "image_input": False,
            "image_output": False,
            "video_input": False,
            "video_output": False,
            "text_to_speech": False,
            "speech_to_text": False,
        },
    },
    "google/gemini-1.0-ultra": {
        "id": "google/gemini-1.0-ultra",
        "name": "Gemini 1.0 Ultra",
        "provider": "google",
        "family": "gemini",
        "context_window": 30720,
        "max_output_tokens": 2048,
        "supports": {
            "text": True,
            "image": True,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": True,
            "structured_output": True,
            "web_search": False,
            "code_execution": False,
        },
        "capabilities": {
            "reasoning_efforts": [],
            "audio_input": False,
            "audio_output": False,
            "image_input": True,
            "image_output": False,
            "video_input": False,
            "video_output": False,
            "text_to_speech": False,
            "speech_to_text": False,
        },
    },
    "google/imagen-3.0-generate-001": {
        "id": "google/imagen-3.0-generate-001",
        "name": "Imagen 3.0",
        "provider": "google",
        "family": "imagen",
        "context_window": 0,
        "max_output_tokens": 0,
        "supports": {
            "text": True,
            "image": True,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": False,
            "structured_output": False,
            "web_search": False,
            "code_execution": False,
            "image_generation": True,
        },
        "capabilities": {
            "image_sizes": ["256x256", "512x512", "1024x1024", "2048x2048"],
            "image_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
        },
    },
    "google/veo-3.0-generate-001": {
        "id": "google/veo-3.0-generate-001",
        "name": "Veo 3.0",
        "provider": "google",
        "family": "veo",
        "context_window": 0,
        "max_output_tokens": 0,
        "supports": {
            "text": True,
            "image": False,
            "audio": False,
            "video": True,
            "reasoning": False,
            "thinking": False,
            "tool_use": False,
            "structured_output": False,
            "web_search": False,
            "code_execution": False,
            "video_generation": True,
        },
        "capabilities": {
            "video_sizes": ["1280x720", "1920x1080"],
            "video_aspect_ratios": ["16:9", "9:16"],
            "max_video_duration_seconds": 8,
        },
    },
    "google/audio-2.0-generate-001": {
        "id": "google/audio-2.0-generate-001",
        "name": "Audio 2.0",
        "provider": "google",
        "family": "audio",
        "context_window": 0,
        "max_output_tokens": 0,
        "supports": {
            "text": True,
            "image": False,
            "audio": True,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": False,
            "structured_output": False,
            "web_search": False,
            "code_execution": False,
            "music_generation": True,
        },
        "capabilities": {
            "max_music_duration_seconds": 30,
        },
    },
    "google/text-embedding-005": {
        "id": "google/text-embedding-005",
        "name": "Text Embedding 005",
        "provider": "google",
        "family": "embedding",
        "context_window": 0,
        "max_output_tokens": 0,
        "supports": {
            "embedding": True,
            "text": True,
            "image": False,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": False,
            "structured_output": False,
            "web_search": False,
            "code_execution": False,
        },
        "capabilities": {
            "embedding_dimensions": 768,
            "max_batch_size": 250,
        },
    },
    "google/text-embedding-004": {
        "id": "google/text-embedding-004",
        "name": "Text Embedding 004",
        "provider": "google",
        "family": "embedding",
        "context_window": 0,
        "max_output_tokens": 0,
        "supports": {
            "embedding": True,
            "text": True,
            "image": False,
            "audio": False,
            "video": False,
            "reasoning": False,
            "thinking": False,
            "tool_use": False,
            "structured_output": False,
            "web_search": False,
            "code_execution": False,
        },
        "capabilities": {
            "embedding_dimensions": 768,
            "max_batch_size": 250,
        },
    },
}

VERTEX_STATIC_CATALOG: Dict[str, Dict[str, Any]] = {}


def build_google_static_catalog_provider(provider: str = "google") -> Dict[str, Any]:
    catalog = GOOGLE_STATIC_CATALOG if provider == "google" else VERTEX_STATIC_CATALOG
    return {
        "provider": provider,
        "models": list(catalog.values()),
        "aliases": GOOGLE_MODEL_ID_ALIASES,
    }


def lookup_google_model_in_catalog(model_id: str, provider: str = "google") -> Optional[Dict[str, Any]]:
    catalog = GOOGLE_STATIC_CATALOG if provider == "google" else VERTEX_STATIC_CATALOG
    normalized = normalize_google_model_id(model_id, provider)
    if normalized in catalog:
        return catalog[normalized]
    alias = GOOGLE_MODEL_ID_ALIASES.get(model_id)
    if alias and alias in catalog:
        return catalog[alias]
    canonical_id, _ = parse_google_model_id(model_id)
    if canonical_id:
        full_id = f"{canonical_id}/{_}"
        if full_id in catalog:
            return catalog[full_id]
    return None


def search_google_catalog(query: str, provider: str = "google") -> List[Dict[str, Any]]:
    catalog = GOOGLE_STATIC_CATALOG if provider == "google" else VERTEX_STATIC_CATALOG
    results = []
    query_lower = query.lower()
    for model_id, model_info in catalog.items():
        if (query_lower in model_id.lower() or
                query_lower in model_info.get("name", "").lower()):
            results.append(model_info)
    return results