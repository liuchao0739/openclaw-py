from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional

from .host.config_utils import (
    CANONICAL_ROOT_MEMORY_FILENAME,
    normalize_agent_id,
    resolve_agent_workspace_dir,
    resolve_state_dir,
    resolve_user_path,
)
from .host.error_utils import format_error_message
from .host.fs_utils import is_path_inside, walk_files
from .host.memory_schema import create_memory_schema
from .host.string_utils import normalize_string_entries


def create_memory_foundation(cfg: dict, agent_id: str) -> dict:
    normalized_agent_id = normalize_agent_id(agent_id)
    workspace_dir = resolve_agent_workspace_dir(cfg, normalized_agent_id)
    state_dir = resolve_state_dir()
    db_path = os.path.join(state_dir, "agents", normalized_agent_id, "memory.db")

    return {
        "agentId": normalized_agent_id,
        "workspaceDir": workspace_dir,
        "stateDir": state_dir,
        "dbPath": db_path,
    }


def ensure_memory_directories(foundation: dict) -> None:
    os.makedirs(foundation["workspaceDir"], exist_ok=True)
    os.makedirs(os.path.dirname(foundation["dbPath"]), exist_ok=True)
    os.makedirs(os.path.join(foundation["workspaceDir"], "memory"), exist_ok=True)


def initialize_memory_db(foundation: dict) -> sqlite3.Connection:
    db_path = foundation["dbPath"]
    conn = sqlite3.connect(db_path)
    try:
        create_memory_schema(conn)
        return conn
    except Exception:
        conn.close()
        raise


def list_memory_files(foundation: dict) -> List[str]:
    workspace_dir = foundation["workspaceDir"]
    results = []
    try:
        canonical_path = os.path.join(workspace_dir, CANONICAL_ROOT_MEMORY_FILENAME)
        if os.path.exists(canonical_path):
            results.append(canonical_path)
        memory_dir = os.path.join(workspace_dir, "memory")
        if os.path.isdir(memory_dir):
            for file_path in walk_files(memory_dir, [".md"]):
                results.append(file_path)
        agent_dir = os.path.join(workspace_dir, "agents")
        if os.path.isdir(agent_dir):
            for file_path in walk_files(agent_dir, [".md"]):
                results.append(file_path)
    except Exception:
        pass
    return results


def resolve_memory_extra_paths(cfg: dict, agent_id: str) -> List[str]:
    normalized_agent_id = normalize_agent_id(agent_id)
    defaults = cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}).get("extraPaths", [])
    agents = cfg.get("agents", {}).get("list", [])
    overrides = []
    if isinstance(agents, list):
        for entry in agents:
            if entry and normalize_agent_id(entry.get("id")) == normalized_agent_id:
                overrides = (entry.get("memorySearch") or {}).get("extraPaths", []) or []
                break

    raw_paths = [*defaults, *overrides]
    return normalize_string_entries(raw_paths)
