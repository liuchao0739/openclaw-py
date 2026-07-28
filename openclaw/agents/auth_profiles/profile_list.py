from __future__ import annotations

from typing import Any

from openclaw.normalization_core.string_normalization import unique_strings
from openclaw.agents.auth_profiles.types import AuthProfileStore


def dedupe_profile_ids(profile_ids: list[str]) -> list[str]:
    return unique_strings(profile_ids)


def list_profiles_for_provider(store: AuthProfileStore, provider: str) -> list[str]:
    from openclaw.agents.provider_auth_aliases import resolve_provider_id_for_auth

    provider_key = resolve_provider_id_for_auth(provider)
    return [
        profile_id
        for profile_id, cred in store.get("profiles", {}).items()
        if resolve_provider_id_for_auth(cred.get("provider", "")) == provider_key
    ]


def resolve_subscription_auth_mode_for_profiles(
    store: AuthProfileStore,
    profile_ids: list[str | None],
) -> str | None:
    for profile_id in profile_ids:
        if not profile_id:
            continue
        cred_type = store.get("profiles", {}).get(profile_id, {}).get("type")
        if cred_type in ("oauth", "token"):
            return cred_type
    return None
