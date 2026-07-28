"""Device pairing access helpers evaluate pairing scopes and role permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .device_auth import normalize_device_auth_scopes


@dataclass
class DevicePairingAccessSummary:
    roles: list[str]
    scopes: list[str]


PendingDeviceApprovalKind = Literal["new-pairing", "role-upgrade", "scope-upgrade", "re-approval"]


@dataclass
class PendingDeviceApprovalState:
    kind: PendingDeviceApprovalKind
    requested: DevicePairingAccessSummary
    approved: DevicePairingAccessSummary | None


def _normalize_unique_single_or_trimmed_string_list(items: Any) -> list[str]:
    if items is None:
        return []
    if isinstance(items, str):
        trimmed = items.strip()
        return [trimmed] if trimmed else []
    if isinstance(items, list):
        result: list[str] = []
        for item in items:
            if isinstance(item, str):
                trimmed = item.strip()
                if trimmed and trimmed not in result:
                    result.append(trimmed)
        return result
    return []


def _normalize_role_list(*items: Any) -> list[str]:
    roles: set[str] = set()
    for item in items:
        for role in _normalize_unique_single_or_trimmed_string_list(item):
            roles.add(role)
    return sorted(roles)


def _includes_all(allowed: list[str], requested: list[str]) -> bool:
    allowed_set = set(allowed)
    return all(value in allowed_set for value in requested)


def summarize_pending_device_access(
    roles: list[str] | None = None,
    role: str | None = None,
    scopes: list[str] | None = None,
) -> DevicePairingAccessSummary:
    return DevicePairingAccessSummary(
        roles=_normalize_role_list(roles, role),
        scopes=normalize_device_auth_scopes(scopes),
    )


def summarize_approved_device_access(
    roles: list[str] | None = None,
    role: str | None = None,
    scopes: list[str] | None = None,
    tokens: Any = None,
) -> DevicePairingAccessSummary:
    approved_roles = _normalize_role_list(roles, role)
    token_list: list[dict[str, Any]] | None = None
    if isinstance(tokens, list):
        token_list = tokens
    elif isinstance(tokens, dict):
        token_list = list(tokens.values())
    active_token_roles = approved_roles
    if token_list is not None:
        active_token_roles = _normalize_role_list(
            [token.get("role", "") for token in token_list if not token.get("revokedAtMs")]
        )
        active_token_roles = [r for r in active_token_roles if r in approved_roles]
    return DevicePairingAccessSummary(
        roles=active_token_roles,
        scopes=normalize_device_auth_scopes(scopes),
    )


def resolve_pending_device_approval_state(
    request_roles: list[str] | None = None,
    request_role: str | None = None,
    request_scopes: list[str] | None = None,
    paired_roles: list[str] | None = None,
    paired_role: str | None = None,
    paired_scopes: list[str] | None = None,
    paired_tokens: Any = None,
) -> PendingDeviceApprovalState:
    requested = summarize_pending_device_access(request_roles, request_role, request_scopes)
    has_paired = any([paired_roles, paired_role, paired_scopes, paired_tokens])
    approved = summarize_approved_device_access(paired_roles, paired_role, paired_scopes, paired_tokens) if has_paired else None
    if approved is None:
        return PendingDeviceApprovalState(kind="new-pairing", requested=requested, approved=None)
    if not _includes_all(approved.roles, requested.roles):
        return PendingDeviceApprovalState(kind="role-upgrade", requested=requested, approved=approved)
    if not _includes_all(approved.scopes, requested.scopes):
        return PendingDeviceApprovalState(kind="scope-upgrade", requested=requested, approved=approved)
    return PendingDeviceApprovalState(kind="re-approval", requested=requested, approved=approved)
