"""Provider auth helpers for plugin SDK consumers.

Mirrors the subset of src/plugin-sdk/provider-auth.ts used by bundled providers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openclaw.agents.auth_profiles.profile_list import (
    list_profiles_for_provider as _list_profiles_for_provider_impl,
)
from openclaw.agents.auth_profiles.store import (
    ensure_auth_profile_store as _ensure_auth_profile_store_impl,
    update_auth_profile_store_with_lock,
)
from openclaw.agents.auth_profiles.types import AuthProfileStore
from openclaw.config.secrets import coerce_secret_ref
from openclaw.utils.normalize_secret_input import (
    normalize_optional_secret_input,
    normalize_secret_input,
)

_PROVIDER_ENV_VARS: dict[str, list[str]] = {
    "alibaba": ["MODELSTUDIO_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"],
    "qwen": ["QWEN_API_KEY", "MODELSTUDIO_API_KEY", "DASHSCOPE_API_KEY"],
    "comfy": ["COMFY_API_KEY", "COMFY_CLOUD_API_KEY"],
}

DEFAULT_SECRET_PROVIDER_ALIAS = "env"
COPILOT_INTEGRATION_ID = "openclaw"
COPILOT_USER_AGENT = "OpenClaw"
COPILOT_EDITOR_PLUGIN_VERSION = "0.0.0"
COPILOT_EDITOR_VERSION = "OpenClaw"
COPILOT_GITHUB_API_VERSION = "2024-11-01"
DEFAULT_COPILOT_API_BASE_URL = "https://api.individual.githubcopilot.com"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

CLAUDE_CLI_PROFILE_ID = "anthropic:claude-cli"
CODEX_CLI_PROFILE_ID = "openai:codex-cli"


def resolve_env_api_key(
    provider: str,
    env: dict[str, str] | None = None,
) -> dict[str, str] | None:
    env_map = env or os.environ
    for env_var in _PROVIDER_ENV_VARS.get(provider, []):
        value = env_map.get(env_var)
        if isinstance(value, str) and value.strip():
            return {"apiKey": value.strip(), "source": env_var}
    return None


def ensure_auth_profile_store(
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    return _ensure_auth_profile_store_impl(agent_dir, options)


def list_profiles_for_provider(store: AuthProfileStore, provider: str) -> list[str]:
    return _list_profiles_for_provider_impl(store, provider)


async def upsert_auth_profile_with_lock(params: dict[str, Any]) -> bool:
    profile_id = params.get("profileId", "")
    credential = params.get("credential", {})
    agent_dir = params.get("agentDir")

    def updater(store: AuthProfileStore) -> bool:
        profiles = store.setdefault("profiles", {})
        profiles[profile_id] = credential
        return True

    result = update_auth_profile_store_with_lock(
        agent_dir=agent_dir,
        updater=updater,
    )
    return result is not None


def apply_auth_profile_config(
    cfg: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    profile_id = params["profileId"]
    provider = params["provider"]
    mode = params["mode"]

    auth = dict(cfg.get("auth", {}))
    existing_profiles = dict(auth.get("profiles", {}))
    existing_profiles[profile_id] = {
        "provider": provider,
        "mode": mode,
    }
    if params.get("email"):
        existing_profiles[profile_id]["email"] = params["email"]
    if params.get("displayName"):
        existing_profiles[profile_id]["displayName"] = params["displayName"]

    order = dict(auth.get("order", {}))
    provider_order = list(order.get(provider, []))
    if profile_id not in provider_order:
        provider_order.insert(0, profile_id)
    order[provider] = provider_order

    auth["profiles"] = existing_profiles
    auth["order"] = order

    result = dict(cfg)
    result["auth"] = auth
    return result


def resolve_default_secret_provider_alias(
    cfg: dict[str, Any] | None,
    source: str = "env",
    prefer_first_provider_for_source: bool = False,
) -> str:
    if prefer_first_provider_for_source:
        providers = (cfg or {}).get("models", {}).get("providers", {})
        if isinstance(providers, dict):
            for provider_id in providers:
                return provider_id
    return DEFAULT_SECRET_PROVIDER_ALIAS


def normalize_secret_input_string(value: Any) -> str | None:
    return normalize_optional_secret_input(value)


def build_token_profile_id(params: dict[str, Any]) -> str:
    provider_id = params.get("providerId", "")
    name = params.get("name", "default")
    return f"{provider_id}:{name}"


def validate_anthropic_setup_token(token: str | None) -> str | None:
    if not token or not isinstance(token, str):
        return "Anthropic setup-token is required."
    normalized = token.strip()
    if not normalized:
        return "Anthropic setup-token cannot be empty."
    return None


def suggest_oauth_profile_id_for_legacy_default(provider: str) -> str:
    return f"{provider}:default"


def is_provider_api_key_configured(params: dict[str, Any]) -> bool:
    provider = params["provider"]
    if resolve_env_api_key(provider):
        return True
    agent_dir = params.get("agentDir")
    if not isinstance(agent_dir, str) or not agent_dir.strip():
        return False
    store = ensure_auth_profile_store(agent_dir, {"allowKeychainPrompt": False})
    profile_ids = list_profiles_for_provider(store, provider)
    profile_types = params.get("profileTypes")
    if not profile_types:
        return len(profile_ids) > 0
    allowed_types = set(profile_types)
    return any(
        store.get("profiles", {}).get(profile_id, {}).get("type") in allowed_types
        for profile_id in profile_ids
    )
