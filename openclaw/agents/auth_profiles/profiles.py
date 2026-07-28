from __future__ import annotations

from typing import Any


def list_auth_profiles(
    store: dict[str, Any],
) -> list[dict[str, Any]]:
    profiles = store.get("profiles", {})
    result: list[dict[str, Any]] = []
    for profile_id, credential in profiles.items():
        result.append({
            "id": profile_id,
            "provider": credential.get("provider"),
            "type": credential.get("type"),
            "displayName": credential.get("displayName", profile_id),
        })
    return result


def get_auth_profile(
    store: dict[str, Any],
    profile_id: str,
) -> dict[str, Any] | None:
    return store.get("profiles", {}).get(profile_id)


def add_auth_profile(
    store: dict[str, Any],
    profile_id: str,
    credential: dict[str, Any],
) -> dict[str, Any]:
    store.setdefault("profiles", {})[profile_id] = credential
    return store


def remove_auth_profile(
    store: dict[str, Any],
    profile_id: str,
) -> dict[str, Any]:
    store.get("profiles", {}).pop(profile_id, None)
    return store
