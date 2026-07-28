from __future__ import annotations

from typing import Any, TypedDict

from ._normalization import normalize_optional_string

AcpSessionInteractionMode = str


class SessionInteractionEntry(TypedDict, total=False):
    spawnedBy: str | None
    parentSessionKey: str | None
    acp: Any | None


def resolve_acp_session_interaction_mode(
    entry: SessionInteractionEntry | None = None,
) -> str:
    if not entry or not entry.get("acp"):
        return "interactive"
    if normalize_optional_string(entry.get("spawnedBy")) or normalize_optional_string(
        entry.get("parentSessionKey")
    ):
        return "parent-owned-background"
    return "interactive"


def is_parent_owned_background_acp_session(entry: SessionInteractionEntry | None = None) -> bool:
    return resolve_acp_session_interaction_mode(entry) == "parent-owned-background"


def is_requester_parent_of_background_acp_session(
    entry: SessionInteractionEntry | None = None,
    requester_session_key: str | None = None,
) -> bool:
    if not is_parent_owned_background_acp_session(entry):
        return False
    requester = normalize_optional_string(requester_session_key)
    if not requester:
        return False
    spawned_by = normalize_optional_string(entry.get("spawnedBy") if entry else None)
    parent_session_key = normalize_optional_string(entry.get("parentSessionKey") if entry else None)
    return requester == spawned_by or requester == parent_session_key