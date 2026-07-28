"""Gateway method policy helpers classify reserved and operator-only gateway methods."""

from __future__ import annotations

from typing import Any

_RESERVED_ADMIN_GATEWAY_METHOD_PREFIXES = [
    "exec.approvals.",
    "config.",
    "wizard.",
    "update.",
]

_RESERVED_ADMIN_GATEWAY_METHOD_SCOPE = "operator.admin"


def _is_reserved_admin_gateway_method(method: str) -> bool:
    return any(method.startswith(prefix) for prefix in _RESERVED_ADMIN_GATEWAY_METHOD_PREFIXES)


def resolve_reserved_gateway_method_scope(method: str) -> str | None:
    if not _is_reserved_admin_gateway_method(method):
        return None
    return _RESERVED_ADMIN_GATEWAY_METHOD_SCOPE


def normalize_plugin_gateway_method_scope(
    method: str,
    scope: str | None = None,
) -> tuple[str | None, bool]:
    reserved_scope = resolve_reserved_gateway_method_scope(method)
    if not reserved_scope or not scope or scope == reserved_scope:
        return (scope, False)
    return (reserved_scope, True)
