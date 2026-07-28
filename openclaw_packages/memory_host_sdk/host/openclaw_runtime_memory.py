from __future__ import annotations

from typing import Any, List, Optional


def get_memory_embedding_provider(provider_id: str, config: Optional[dict] = None) -> Optional[object]:
    return None


def list_memory_embedding_providers() -> list:
    return []


def list_registered_memory_embedding_providers() -> list:
    return []


def list_registered_memory_embedding_provider_adapters() -> list:
    return []


def resolve_canonical_root_memory_file(workspace_dir: str) -> Optional[str]:
    import os
    from .config_utils import CANONICAL_ROOT_MEMORY_FILENAME
    path = os.path.join(workspace_dir, CANONICAL_ROOT_MEMORY_FILENAME)
    if os.path.exists(path):
        return path
    return None


def should_skip_root_memory_auxiliary_path(workspace_dir: str, abs_path: str) -> bool:
    return False


def empty_plugin_config_schema() -> dict:
    return {"type": "object", "properties": {}}


def build_active_memory_prompt_section(cfg: dict, agent_id: str) -> str:
    return ""


def get_memory_capability_registration() -> dict:
    return {}


def list_active_memory_public_artifacts() -> list:
    return []
