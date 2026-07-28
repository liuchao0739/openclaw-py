from __future__ import annotations

from typing import Any


def build_effective_oauth_config(
    store: dict[str, Any] | None = None,
    profile_id: str | None = None,
) -> dict[str, Any]:
    store = store or {}
    if not profile_id:
        return {}
    credential = store.get("profiles", {}).get(profile_id)
    if not credential or credential.get("type") != "oauth":
        return {}
    return {
        "provider": credential.get("provider"),
        "clientId": credential.get("clientId"),
        "refreshToken": credential.get("refreshToken"),
    }
