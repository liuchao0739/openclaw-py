from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .host.config_utils import normalize_agent_id, resolve_state_dir
from .host.embeddings import EmbeddingProvider, create_noop_embedding_provider
from .host.embeddings_storage import EmbeddingStorage
from .host.memory_schema import create_memory_schema


class MemoryEmbeddingsEngine:
    def __init__(self, cfg: dict, agent_id: str):
        self._cfg = cfg
        self._agent_id = normalize_agent_id(agent_id)
        state_dir = resolve_state_dir()
        storage_path = os.path.join(state_dir, "agents", self._agent_id, "embeddings.db")
        self._storage = EmbeddingStorage(storage_path)
        self._provider: Optional[EmbeddingProvider] = None

    @property
    def storage(self) -> EmbeddingStorage:
        return self._storage

    def get_provider(self) -> EmbeddingProvider:
        if not self._provider:
            self._provider = create_noop_embedding_provider()
        return self._provider

    def set_provider(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def create_embedding(
        self,
        text: str,
        session_key: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        provider = self.get_provider()
        embedding = provider.fetch(text, session_key or "")
        entry_id = f"{session_key or 'global'}:{hash(text)}"
        self._storage.store(
            entry_id=entry_id,
            text=text,
            embedding=embedding,
            dimensions=len(embedding),
            model=provider.model_id if hasattr(provider, "model_id") else None,
            session_key=session_key,
        )
        return {
            "entryId": entry_id,
            "embedding": embedding,
            "dimensions": len(embedding),
        }

    def batch_create_embeddings(
        self,
        inputs: List[Dict[str, Any]],
        opts: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        provider = self.get_provider()
        results = []
        for inp in inputs:
            text = inp.get("text", "")
            session_key = inp.get("sessionKey", "")
            try:
                embedding = provider.fetch(text, session_key)
                results.append({
                    "entryId": f"{session_key}:{hash(text)}",
                    "text": text,
                    "embedding": embedding,
                    "dimensions": len(embedding),
                })
            except Exception:
                results.append({
                    "entryId": f"{session_key}:{hash(text)}",
                    "text": text,
                    "error": "Embedding failed",
                })
        return results
