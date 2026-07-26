"""Provider auth helpers for plugin SDK consumers.

Mirrors the subset of src/plugin-sdk/provider-auth.ts used by bundled providers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_PROVIDER_ENV_VARS: dict[str, list[str]] = {
    "alibaba": ["MODELSTUDIO_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"],
    "qwen": ["QWEN_API_KEY", "MODELSTUDIO_API_KEY", "DASHSCOPE_API_KEY"],
    "comfy": ["COMFY_API_KEY", "COMFY_CLOUD_API_KEY"],
}


def resolve_env_api_key(
    provider: str,
    env: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Resolve a provider API key from known environment variables."""
    env_map = env or os.environ
    for env_var in _PROVIDER_ENV_VARS.get(provider, []):
        value = env_map.get(env_var)
        if isinstance(value, str) and value.strip():
            return {"apiKey": value.strip(), "source": env_var}
    return None


def _list_profiles_for_provider(agent_dir: str, provider: str) -> list[str]:
    auth_store_path = Path(agent_dir) / "auth-profiles.json"
    if not auth_store_path.is_file():
        return []
    try:
        payload = json.loads(auth_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, dict):
        return []
    return [
        profile_id
        for profile_id, profile in profiles.items()
        if isinstance(profile, dict) and profile.get("provider") == provider
    ]


def is_provider_api_key_configured(params: dict[str, Any]) -> bool:
    """Check whether a provider has env auth or matching local auth profiles configured."""
    provider = params["provider"]
    if resolve_env_api_key(provider):
        return True
    agent_dir = params.get("agentDir")
    if not isinstance(agent_dir, str) or not agent_dir.strip():
        return False
    profile_ids = _list_profiles_for_provider(agent_dir.strip(), provider)
    profile_types = params.get("profileTypes")
    if not profile_types:
        return len(profile_ids) > 0
    auth_store_path = Path(agent_dir.strip()) / "auth-profiles.json"
    if not auth_store_path.is_file():
        return False
    try:
        payload = json.loads(auth_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, dict):
        return False
    allowed_types = set(profile_types)
    return any(
        isinstance(profiles.get(profile_id), dict)
        and profiles[profile_id].get("type") in allowed_types
        for profile_id in profile_ids
    )
