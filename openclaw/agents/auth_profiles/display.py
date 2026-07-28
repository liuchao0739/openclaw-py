from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.identity import resolve_auth_profile_metadata
from openclaw.agents.auth_profiles.types import AuthProfileStore


def resolve_auth_profile_display_label(
    cfg: dict[str, Any] | None = None,
    store: AuthProfileStore | None = None,
    profile_id: str = "",
) -> str:
    metadata = resolve_auth_profile_metadata(cfg=cfg, store=store, profile_id=profile_id)
    display_name = metadata.get("displayName")
    if display_name:
        return f"{profile_id} ({display_name})"
    email = metadata.get("email")
    if email:
        return f"{profile_id} ({email})"
    return profile_id
