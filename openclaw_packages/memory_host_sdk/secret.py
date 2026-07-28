from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .host.config_utils import resolve_state_dir, resolve_user_path
from .host.error_utils import format_error_message, redact_sensitive_text
from .host.secret_input import resolve_memory_secret_input_string


def resolve_secret_input(
    cfg: dict,
    agent_id: str,
    path: str,
    fallback: Optional[str] = None,
) -> Optional[str]:
    raw = (cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}) or {}).get("secrets", {}).get(path)
    if raw is None:
        agents = cfg.get("agents", {}).get("list", [])
        if isinstance(agents, list):
            for entry in agents:
                if entry.get("id") == agent_id:
                    raw = (entry.get("memorySearch", {}) or {}).get("secrets", {}).get(path)
                    break

    if raw is None:
        return fallback

    return resolve_memory_secret_input_string(raw, path)


def has_secret_input(cfg: dict, agent_id: str, path: str) -> bool:
    raw = (cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}) or {}).get("secrets", {}).get(path)
    if raw is not None:
        return True
    agents = cfg.get("agents", {}).get("list", [])
    if isinstance(agents, list):
        for entry in agents:
            if entry.get("id") == agent_id:
                raw = (entry.get("memorySearch", {}) or {}).get("secrets", {}).get(path)
                return raw is not None
    return False
