"""Operator scope compatibility helpers normalize legacy operator role names."""

from __future__ import annotations

from typing import Any


_OPERATOR_ROLE = "operator"
_OPERATOR_ADMIN_SCOPE = "operator.admin"
_OPERATOR_READ_SCOPE = "operator.read"
_OPERATOR_WRITE_SCOPE = "operator.write"
_OPERATOR_SCOPE_PREFIX = "operator."


def _normalize_scope_list(scopes: list[str]) -> list[str]:
    out: set[str] = set()
    for scope in scopes:
        trimmed = scope.strip()
        if trimmed:
            out.add(trimmed)
    return sorted(out)


def _operator_scope_satisfied(requested_scope: str, granted: set[str]) -> bool:
    if not requested_scope.startswith(_OPERATOR_SCOPE_PREFIX):
        return False
    if _OPERATOR_ADMIN_SCOPE in granted:
        return True
    if requested_scope == _OPERATOR_READ_SCOPE:
        return _OPERATOR_READ_SCOPE in granted or _OPERATOR_WRITE_SCOPE in granted
    if requested_scope == _OPERATOR_WRITE_SCOPE:
        return _OPERATOR_WRITE_SCOPE in granted
    return requested_scope in granted


def role_scopes_allow(
    role: str,
    requested_scopes: list[str],
    allowed_scopes: list[str],
) -> bool:
    requested = _normalize_scope_list(requested_scopes)
    if len(requested) == 0:
        return True
    allowed = _normalize_scope_list(allowed_scopes)
    if len(allowed) == 0:
        return False
    allowed_set = set(allowed)
    if role.strip() != _OPERATOR_ROLE:
        prefix = f"{role.strip()}."
        return all(scope.startswith(prefix) and scope in allowed_set for scope in requested)
    return all(_operator_scope_satisfied(scope, allowed_set) for scope in requested)


def resolve_missing_requested_scope(
    role: str,
    requested_scopes: list[str],
    allowed_scopes: list[str],
) -> str | None:
    for scope in requested_scopes:
        if not role_scopes_allow(role, [scope], allowed_scopes):
            return scope
    return None


def resolve_scope_outside_requested_roles(
    requested_roles: list[str],
    requested_scopes: list[str],
) -> str | None:
    for scope in requested_scopes:
        if not any(
            role_scopes_allow(role, [scope], [scope])
            for role in requested_roles
        ):
            return scope
    return None
