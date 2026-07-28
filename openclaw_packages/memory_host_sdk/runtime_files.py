from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .host.config_utils import (
    CANONICAL_ROOT_MEMORY_FILENAME,
    normalize_agent_id,
    resolve_agent_workspace_dir,
    resolve_state_dir,
)
from .host.fs_utils import is_path_inside, walk_files
from .host.hash import hash_text
from .host.read_file import read_memory_file
from .host.string_utils import unique_strings


def list_memory_files(agent_id: str, cfg: dict) -> List[Dict[str, Any]]:
    normalized = normalize_agent_id(agent_id)
    workspace = resolve_agent_workspace_dir(cfg, normalized)
    results = []

    canonical = os.path.join(workspace, CANONICAL_ROOT_MEMORY_FILENAME)
    if os.path.exists(canonical):
        stat = os.stat(canonical)
        results.append({
            "path": canonical,
            "name": CANONICAL_ROOT_MEMORY_FILENAME,
            "size": stat.st_size,
            "hash": hash_text(canonical),
        })

    memory_dir = os.path.join(workspace, "memory")
    if os.path.isdir(memory_dir):
        for path in walk_files(memory_dir, [".md"]):
            try:
                stat = os.stat(path)
                results.append({
                    "path": path,
                    "name": os.path.basename(path),
                    "size": stat.st_size,
                    "hash": hash_text(path),
                })
            except OSError:
                pass

    return results


def read_memory_content(file_path: str) -> Optional[str]:
    return read_memory_file(file_path)


def resolve_workspace_dir(cfg: dict, agent_id: str) -> str:
    return resolve_agent_workspace_dir(cfg, normalize_agent_id(agent_id))
