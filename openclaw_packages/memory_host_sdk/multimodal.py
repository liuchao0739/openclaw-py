from __future__ import annotations

from typing import Any, Dict, List, Optional

from .host.multimodal import (
    MemoryMultimodalSettings,
    is_memory_multimodal_enabled,
    normalize_memory_multimodal_settings,
)


def get_multimodal_settings(cfg: dict, agent_id: Optional[str] = None) -> MemoryMultimodalSettings:
    return normalize_memory_multimodal_settings(
        (cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}) or {}).get("multimodal", {})
    )


def is_multimodal_enabled(cfg: dict, agent_id: Optional[str] = None) -> bool:
    settings = get_multimodal_settings(cfg, agent_id)
    return is_memory_multimodal_enabled(settings)


def list_supported_modalities() -> List[str]:
    return ["text", "image", "audio"]
