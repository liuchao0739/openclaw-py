from __future__ import annotations

from typing import Any

from openclaw.config.types_models import normalize_optional_string
from openclaw.agents.auth_profiles.types import AuthProfileStore


def build_auth_profile_id(
    provider_id: str,
    profile_name: str | None = None,
    profile_prefix: str | None = None,
) -> str:
    prefix = normalize_optional_string(profile_prefix) or provider_id
    name = normalize_optional_string(profile_name) or "default"
    return f"{prefix}:{name}"


def resolve_stored_metadata(
    store: AuthProfileStore | None,
    profile_id: str,
) -> dict[str, Any]:
    profile = store.get("profiles", {}).get(profile_id) if store else None
    if not profile:
        return {}
    result: dict[str, Any] = {}
    if "displayName" in profile:
        result["displayName"] = normalize_optional_string(profile.get("displayName"))
    if "email" in profile:
        result["email"] = normalize_optional_string(profile.get("email"))
    return result


def resolve_auth_profile_metadata(
    cfg: dict[str, Any] | None = None,
    store: AuthProfileStore | None = None,
    profile_id: str = "",
) -> dict[str, Any]:
    configured = (cfg.get("auth", {}).get("profiles", {}) or {}).get(profile_id) if cfg else None
    stored = resolve_stored_metadata(store, profile_id)
    return {
        "displayName": normalize_optional_string(
            configured.get("displayName") if configured else None
        )
        or stored.get("displayName"),
        "email": normalize_optional_string(
            configured.get("email") if configured else None
        )
        or stored.get("email"),
    }
