"""Device auth helpers normalize roles and scopes for device authorization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeviceAuthEntry:
    token: str
    role: str
    scopes: list[str]
    updated_at_ms: int


@dataclass
class DeviceAuthStore:
    version: int
    device_id: str
    tokens: dict[str, DeviceAuthEntry]


def normalize_device_auth_role(role: str) -> str:
    return role.strip()


def normalize_device_auth_scopes(scopes: list[Any] | None) -> list[str]:
    if not isinstance(scopes, list):
        return []
    out: set[str] = set()
    for scope in scopes:
        if not isinstance(scope, str):
            continue
        trimmed = scope.strip()
        if trimmed:
            out.add(trimmed)
    if "operator.admin" in out:
        out.add("operator.read")
        out.add("operator.write")
    elif "operator.write" in out:
        out.add("operator.read")
    return sorted(out)
