from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.constants import AUTH_STORE_VERSION
from openclaw.agents.auth_profiles.types import (
    AuthProfileCredential,
    AuthProfileSecretsStore,
    AuthProfileStore,
)


def has_agent_copy_override(credential: AuthProfileCredential) -> bool | None:
    val = credential.get("copyToAgents")
    return val if isinstance(val, bool) else None


def has_copyable_oauth_material(credential: AuthProfileCredential) -> bool:
    if credential.get("type") != "oauth":
        return False
    for field in ("access", "refresh"):
        val = credential.get(field)
        if isinstance(val, str) and val.strip():
            return True
    return False


def resolve_auth_profile_portability(
    credential: AuthProfileCredential,
) -> dict[str, Any]:
    override = has_agent_copy_override(credential)
    if override is False:
        return {"portable": False, "reason": "credential-opted-out"}
    if credential.get("type") == "oauth":
        if not has_copyable_oauth_material(credential):
            return {
                "portable": False,
                "reason": "non-portable-oauth-refresh-token",
            }
        if override is True:
            return {"portable": True, "reason": "oauth-provider-opted-in"}
        return {"portable": False, "reason": "non-portable-oauth-refresh-token"}
    return {"portable": True, "reason": "portable-static-credential"}


def is_auth_profile_credential_portable_for_agent_copy(
    credential: AuthProfileCredential,
) -> bool:
    return resolve_auth_profile_portability(credential)["portable"]


def build_portable_auth_profile_secrets_store_for_agent_copy(
    store: AuthProfileStore,
) -> dict[str, Any]:
    copied_profile_ids: list[str] = []
    skipped_profile_ids: list[str] = []
    profiles: dict[str, AuthProfileCredential] = {}

    for profile_id, credential in store.get("profiles", {}).items():
        if not is_auth_profile_credential_portable_for_agent_copy(credential):
            skipped_profile_ids.append(profile_id)
            continue
        copied_profile_ids.append(profile_id)
        profiles[profile_id] = credential

    return {
        "store": {"version": AUTH_STORE_VERSION, "profiles": profiles},
        "copiedProfileIds": copied_profile_ids,
        "skippedProfileIds": skipped_profile_ids,
    }
