"""Device bootstrap profile helpers build profile claims for device onboarding."""

from __future__ import annotations

from dataclasses import dataclass

from .device_auth import normalize_device_auth_role, normalize_device_auth_scopes


BOOTSTRAP_HANDOFF_OPERATOR_SCOPES = [
    "operator.approvals",
    "operator.read",
    "operator.talk.secrets",
    "operator.write",
]

_BOOTSTRAP_HANDOFF_OPERATOR_SCOPE_SET = set(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES)

PAIRING_SETUP_BOOTSTRAP_PROFILE: dict[str, list[str]] = {
    "roles": ["node", "operator"],
    "scopes": list(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES),
}


def _normalize_bootstrap_roles(roles: list[str] | None) -> list[str]:
    if not isinstance(roles, list):
        return []
    out: set[str] = set()
    for role in roles:
        normalized = normalize_device_auth_role(role)
        if normalized:
            out.add(normalized)
    return sorted(out)


def normalize_device_bootstrap_profile(
    roles: list[str] | None = None,
    scopes: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "roles": _normalize_bootstrap_roles(roles),
        "scopes": normalize_device_auth_scopes(scopes if scopes else []),
    }


def is_pairing_setup_bootstrap_profile(
    roles: list[str] | None = None,
    scopes: list[str] | None = None,
) -> bool:
    profile = normalize_device_bootstrap_profile(roles, scopes)
    if len(profile["roles"]) != len(PAIRING_SETUP_BOOTSTRAP_PROFILE["roles"]):
        return False
    if len(profile["scopes"]) != len(PAIRING_SETUP_BOOTSTRAP_PROFILE["scopes"]):
        return False
    return (
        all(r == p for r, p in zip(profile["roles"], PAIRING_SETUP_BOOTSTRAP_PROFILE["roles"]))
        and all(s == p for s, p in zip(profile["scopes"], PAIRING_SETUP_BOOTSTRAP_PROFILE["scopes"]))
    )


def resolve_bootstrap_profile_scopes_for_role(role: str, scopes: list[str]) -> list[str]:
    normalized_role = normalize_device_auth_role(role)
    normalized_scopes = normalize_device_auth_scopes(list(scopes))
    if normalized_role == "operator":
        return [s for s in normalized_scopes if s in _BOOTSTRAP_HANDOFF_OPERATOR_SCOPE_SET]
    return []


def resolve_bootstrap_profile_scopes_for_roles(roles: list[str], scopes: list[str]) -> list[str]:
    all_scopes: list[str] = []
    for role in roles:
        all_scopes.extend(resolve_bootstrap_profile_scopes_for_role(role, scopes))
    return normalize_device_auth_scopes(all_scopes)


def normalize_device_bootstrap_handoff_profile(
    roles: list[str] | None = None,
    scopes: list[str] | None = None,
) -> dict[str, list[str]]:
    profile = normalize_device_bootstrap_profile(roles, scopes)
    return {
        "roles": profile["roles"],
        "scopes": resolve_bootstrap_profile_scopes_for_roles(profile["roles"], profile["scopes"]),
    }
