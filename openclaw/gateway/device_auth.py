"""Gateway-client device auth helpers.

Mirrors src/gateway/device-auth.ts (barrel re-export). Stub implementations
since the gateway-client package is not yet ported.
"""

from __future__ import annotations

from typing import Any, Mapping


def build_device_auth_payload(params: Mapping[str, Any]) -> dict[str, Any]:
    """Build a device auth payload (stub)."""
    return dict(params)


def build_device_auth_payload_v3(params: Mapping[str, Any]) -> dict[str, Any]:
    """Build a device auth payload v3 (stub)."""
    return dict(params)


def normalize_device_metadata_for_auth(metadata: Any) -> dict[str, Any]:
    """Normalize device metadata for auth (stub)."""
    if isinstance(metadata, Mapping):
        return {k: v for k, v in metadata.items() if v is not None}
    return {}
