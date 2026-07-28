from __future__ import annotations

import os
import threading
from typing import Any


_agent_dir_registry: dict[str, str] = {}
_lock = threading.Lock()


def register_agent_dir(agent_id: str, dir_path: str) -> None:
    with _lock:
        _agent_dir_registry[agent_id] = os.path.expanduser(dir_path)


def unregister_agent_dir(agent_id: str) -> None:
    with _lock:
        _agent_dir_registry.pop(agent_id, None)


def resolve_registered_agent_id_for_dir(dir_path: str) -> str | None:
    normalized = os.path.normpath(os.path.expanduser(dir_path))
    with _lock:
        for agent_id, registered_dir in _agent_dir_registry.items():
            if os.path.normpath(registered_dir) == normalized:
                return agent_id
    return None


def resolve_registered_dir_for_agent_id(agent_id: str) -> str | None:
    with _lock:
        return _agent_dir_registry.get(agent_id)


def clear_agent_dir_registry() -> None:
    with _lock:
        _agent_dir_registry.clear()
