"""Locates root memory files that seed agent context.

Mirrors src/memory/root-memory-files.ts.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

CANONICAL_ROOT_MEMORY_FILENAME = "MEMORY.md"
LEGACY_ROOT_MEMORY_FILENAME = "memory.md"
ROOT_MEMORY_REPAIR_RELATIVE_DIR = ".openclaw-repair/root-memory"


def resolve_canonical_root_memory_path(workspace_dir: str) -> str:
    """Resolve the canonical root memory file path for a workspace."""
    return str(Path(workspace_dir) / CANONICAL_ROOT_MEMORY_FILENAME)


def resolve_legacy_root_memory_path(workspace_dir: str) -> str:
    """Resolve the legacy root memory file path for a workspace."""
    return str(Path(workspace_dir) / LEGACY_ROOT_MEMORY_FILENAME)


def resolve_root_memory_repair_dir(workspace_dir: str) -> str:
    """Resolve the repair directory used while migrating root memory files."""
    return str(Path(workspace_dir) / ".openclaw-repair" / "root-memory")


def _normalize_workspace_relative_path(value: str) -> str:
    return re.sub(r"^\.\/", "", value.replace("\\", "/").strip())


async def exact_workspace_entry_exists(dir: str, name: str) -> bool:
    """Check for an exact directory entry without case-folded path lookup."""
    try:
        entries = await _async_listdir(dir)
        return name in entries
    except Exception:
        return False


async def _async_listdir(dir: str) -> list[str]:
    """Async list directory entries."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.listdir, dir)


async def resolve_canonical_root_memory_file(workspace_dir: str) -> str | None:
    """Resolve the canonical root memory file only when it is a real file, not a symlink."""
    try:
        entries = await _async_listdir(workspace_dir)
        for entry in entries:
            if entry == CANONICAL_ROOT_MEMORY_FILENAME:
                full_path = Path(workspace_dir) / entry
                if full_path.is_file() and not full_path.is_symlink():
                    return str(full_path)
    except Exception:
        pass
    return None


def should_skip_root_memory_auxiliary_path(
    params: dict[str, str],
) -> bool:
    """Skip legacy/repair root memory paths when scanning workspace memory files."""
    workspace_dir = params["workspaceDir"]
    abs_path = params["absPath"]
    try:
        relative = os.path.relpath(abs_path, workspace_dir)
    except ValueError:
        return False
    if relative.startswith("..") or os.path.isabs(relative):
        return False
    normalized = _normalize_workspace_relative_path(relative)
    return (
        normalized == LEGACY_ROOT_MEMORY_FILENAME
        or normalized == ROOT_MEMORY_REPAIR_RELATIVE_DIR
        or normalized.startswith(f"{ROOT_MEMORY_REPAIR_RELATIVE_DIR}/")
    )
