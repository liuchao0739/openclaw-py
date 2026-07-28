from __future__ import annotations

from typing import Optional

from .multimodal import MemoryMultimodalSettings


def is_memory_multimodal_enabled(settings: MemoryMultimodalSettings) -> bool:
    return settings.enabled and len(settings.modalities) > 0


def normalize_memory_multimodal_settings(raw: dict) -> MemoryMultimodalSettings:
    from .multimodal import normalize_memory_multimodal_settings as _normalize
    return _normalize(raw)
