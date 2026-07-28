from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import host
from .host.backend_config import resolve_memory_backend_config
from .host.batch_runner import BatchRunner
from .host.config_utils import (
    DEFAULT_AGENT_ID,
    normalize_agent_id,
    parse_duration_ms,
    resolve_agent_workspace_dir,
    resolve_default_agent_id,
    resolve_state_dir,
    resolve_user_path,
)
from .host.error_utils import format_error_message
from .host.embeddings import EmbeddingProvider, create_noop_embedding_provider
from .host.embeddings_storage import EmbeddingStorage
from .host.fs_utils import is_path_inside
from .host.types import (
    MemorySearchResult,
    MemoryEmbeddingProbeResult,
)


def create_engine(cfg: dict, agent_id: str) -> "MemoryHostEngine":
    return MemoryHostEngine(cfg, agent_id)


class MemoryHostEngine:
    def __init__(self, cfg: dict, agent_id: str):
        self._cfg = cfg
        self._agent_id = normalize_agent_id(agent_id)
        self._workspace_dir = resolve_agent_workspace_dir(cfg, self._agent_id)
        self._backend = resolve_memory_backend_config(cfg, self._agent_id)
        self._embedding_provider: Optional[EmbeddingProvider] = None
        self._embedding_storage: Optional[EmbeddingStorage] = None
        self._batch_runner: Optional[BatchRunner] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def workspace_dir(self) -> str:
        return self._workspace_dir

    @property
    def backend(self) -> dict:
        return self._backend

    def get_embedding_provider(self) -> EmbeddingProvider:
        if not self._embedding_provider:
            self._embedding_provider = create_noop_embedding_provider()
        return self._embedding_provider

    def get_embedding_storage(self) -> EmbeddingStorage:
        if not self._embedding_storage:
            import os
            state_dir = resolve_state_dir()
            db_path = os.path.join(state_dir, "agents", self._agent_id, "embeddings.db")
            self._embedding_storage = EmbeddingStorage(db_path)
        return self._embedding_storage

    def get_batch_runner(self) -> BatchRunner:
        if not self._batch_runner:
            self._batch_runner = BatchRunner(self._cfg, self._agent_id)
        return self._batch_runner

    def search(self, query: str, limit: int = 5, include_citations: bool = True) -> List[MemorySearchResult]:
        return []

    def probe_embedding(self, text: str, session_key: Optional[str] = None) -> MemoryEmbeddingProbeResult:
        return MemoryEmbeddingProbeResult(
            success=False,
            dimensions=0,
            error="No embedding provider configured",
        )

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        self._embedding_provider = provider

    def close(self) -> None:
        if self._batch_runner:
            self._batch_runner.close()
