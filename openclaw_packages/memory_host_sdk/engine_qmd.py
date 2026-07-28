from __future__ import annotations

from typing import Any, Dict, List, Optional

from .host.backend_config import resolve_memory_backend_config
from .host.config_utils import normalize_agent_id, resolve_agent_workspace_dir


class MemoryQmdEngine:
    def __init__(self, cfg: dict, agent_id: str):
        self._cfg = cfg
        self._agent_id = normalize_agent_id(agent_id)
        self._backend = resolve_memory_backend_config(cfg, self._agent_id)

    @property
    def backend(self) -> dict:
        return self._backend

    @property
    def is_qmd_backend(self) -> bool:
        return self._backend.get("backend") == "qmd"

    def search(
        self,
        query: str,
        session_key: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_qmd_backend:
            return []
        return []

    def update_index(self, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.is_qmd_backend:
            return {"ok": False, "error": "qmd backend not configured"}
        return {"ok": True}

    def close(self) -> None:
        pass
