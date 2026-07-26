"""Provider auth runtime helpers for plugin SDK consumers.

Mirrors the subset of src/plugin-sdk/provider-auth-runtime.ts used by bundled providers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.provider_auth import resolve_env_api_key


async def resolve_api_key_for_provider(params: dict[str, Any]) -> dict[str, str | None]:
    """Resolve provider API-key auth from config, env, or auth profiles."""
    provider = params["provider"]
    env_auth = resolve_env_api_key(provider)
    if env_auth:
        return {"apiKey": env_auth["apiKey"], "source": env_auth["source"]}

    cfg = params.get("cfg")
    if isinstance(cfg, dict):
        models = cfg.get("models")
        providers = models.get("providers") if isinstance(models, dict) else None
        provider_cfg = providers.get(provider) if isinstance(providers, dict) else None
        if isinstance(provider_cfg, dict):
            api_key = provider_cfg.get("apiKey")
            if isinstance(api_key, str) and api_key.strip():
                return {"apiKey": api_key.strip(), "source": f"models.providers.{provider}.apiKey"}

    store = params.get("store") or params.get("authStore")
    if isinstance(store, dict):
        profiles = store.get("profiles")
        if isinstance(profiles, dict):
            for profile in profiles.values():
                if not isinstance(profile, dict) or profile.get("provider") != provider:
                    continue
                if profile.get("type") == "api_key":
                    key = profile.get("key")
                    if isinstance(key, str) and key.strip():
                        return {"apiKey": key.strip(), "source": "auth-profile"}

    agent_dir = params.get("agentDir")
    if isinstance(agent_dir, str) and agent_dir.strip():
        auth_store_path = Path(agent_dir.strip()) / "auth-profiles.json"
        if auth_store_path.is_file():
            try:
                payload = json.loads(auth_store_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            profiles = payload.get("profiles") if isinstance(payload, dict) else None
            if isinstance(profiles, dict):
                for profile in profiles.values():
                    if not isinstance(profile, dict) or profile.get("provider") != provider:
                        continue
                    if profile.get("type") == "api_key":
                        key = profile.get("key")
                        if isinstance(key, str) and key.strip():
                            return {"apiKey": key.strip(), "source": "auth-profile"}

    return {"apiKey": None}
