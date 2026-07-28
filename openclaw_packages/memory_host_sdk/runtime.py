from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import host
from .engine import MemoryHostEngine, create_engine
from .engine_foundation import (
    create_memory_foundation,
    ensure_memory_directories,
    initialize_memory_db,
    list_memory_files,
    resolve_memory_extra_paths,
)
from .engine_storage import MemoryStorage, create_memory_storage
from .engine_embeddings import MemoryEmbeddingsEngine
from .engine_qmd import MemoryQmdEngine
from .host.config_utils import normalize_agent_id, resolve_default_agent_id
from .host.multimodal import (
    MemoryMultimodalSettings,
    is_memory_multimodal_enabled,
    normalize_memory_multimodal_settings,
)


class MemoryHostRuntime:
    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._default_agent_id = resolve_default_agent_id(cfg)
        self._engines: Dict[str, MemoryHostEngine] = {}
        self._multimodal: MemoryMultimodalSettings = normalize_memory_multimodal_settings(
            (cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}) or {}).get("multimodal", {})
        )

    @property
    def config(self) -> dict:
        return self._cfg

    @property
    def default_agent_id(self) -> str:
        return self._default_agent_id

    @property
    def multimodal(self) -> MemoryMultimodalSettings:
        return self._multimodal

    def get_engine(self, agent_id: Optional[str] = None) -> MemoryHostEngine:
        target = normalize_agent_id(agent_id or self._default_agent_id)
        if target not in self._engines:
            self._engines[target] = create_engine(self._cfg, target)
        return self._engines[target]

    def get_multimodal_enabled(self) -> bool:
        return is_memory_multimodal_enabled(self._multimodal)

    def close(self) -> None:
        for engine in self._engines.values():
            engine.close()
        self._engines.clear()


def create_runtime(cfg: dict) -> MemoryHostRuntime:
    return MemoryHostRuntime(cfg)
