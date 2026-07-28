from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List

from .hash import hash_text
from .string_utils import normalize_lowercase_string_or_empty

MEMORY_MULTIMODAL_SPECS = {
    "image": {
        "labelPrefix": "Image file",
        "extensions": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"],
    },
    "audio": {
        "labelPrefix": "Audio file",
        "extensions": [".mp3", ".wav", ".ogg", ".opus", ".m4a", ".aac", ".flac"],
    },
}

MEMORY_MULTIMODAL_MODALITIES = list(MEMORY_MULTIMODAL_SPECS.keys())
DEFAULT_MEMORY_MULTIMODAL_MAX_FILE_BYTES = 10 * 1024 * 1024


@dataclass
class MemoryMultimodalSettings:
    enabled: bool
    modalities: List[str]
    max_file_bytes: int


@dataclass
class MemoryFileEntry:
    path: str
    abs_path: str
    mtime_ms: float
    size: int
    hash: str
    data_hash: Optional[str] = None
    kind: Optional[str] = None
    content_text: Optional[str] = None
    modality: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class MemoryChunk:
    start_line: int
    end_line: int
    text: str
    hash: str
    embedding_input: Optional[dict] = None


@dataclass
class MultimodalMemoryChunk:
    chunk: MemoryChunk
    structured_input_bytes: int


DISABLED_MULTIMODAL_SETTINGS = MemoryMultimodalSettings(
    enabled=False,
    modalities=[],
    max_file_bytes=0,
)


def normalize_memory_multimodal_modalities(raw: Optional[List[str]]) -> List[str]:
    if raw is None or "all" in raw:
        return list(MEMORY_MULTIMODAL_MODALITIES)
    normalized = set()
    for value in raw:
        if value in ("image", "audio"):
            normalized.add(value)
    return list(normalized)


def normalize_memory_multimodal_settings(raw: dict) -> MemoryMultimodalSettings:
    enabled = raw.get("enabled") is True
    max_file_bytes = raw.get("maxFileBytes")
    if not isinstance(max_file_bytes, (int, float)) or not (max_file_bytes == max_file_bytes) or max_file_bytes <= 0:
        max_file_bytes = DEFAULT_MEMORY_MULTIMODAL_MAX_FILE_BYTES
    max_file_bytes = max(1, int(max_file_bytes))
    return MemoryMultimodalSettings(
        enabled=enabled,
        modalities=normalize_memory_multimodal_modalities(raw.get("modalities")),
        max_file_bytes=max_file_bytes,
    )


def is_memory_multimodal_enabled(settings: MemoryMultimodalSettings) -> bool:
    return settings.enabled and len(settings.modalities) > 0


def get_memory_multimodal_extensions(modality: str) -> list:
    return MEMORY_MULTIMODAL_SPECS.get(modality, {}).get("extensions", [])


def build_memory_multimodal_label(modality: str, normalized_path: str) -> str:
    prefix = MEMORY_MULTIMODAL_SPECS.get(modality, {}).get("labelPrefix", "File")
    return f"{prefix}: {normalized_path}"


def build_case_insensitive_extension_glob(extension: str) -> str:
    normalized = normalize_lowercase_string_or_empty(extension).lstrip(".")
    if not normalized:
        return "*"
    parts = [f"[{c.lower()}{c.upper()}]" for c in normalized]
    return f"*.{''.join(parts)}"


def classify_memory_multimodal_path(
    file_path: str,
    settings: MemoryMultimodalSettings,
) -> Optional[str]:
    if not is_memory_multimodal_enabled(settings):
        return None
    lower = normalize_lowercase_string_or_empty(file_path)
    for modality in settings.modalities:
        for extension in get_memory_multimodal_extensions(modality):
            if lower.endswith(extension):
                return modality
    return None
