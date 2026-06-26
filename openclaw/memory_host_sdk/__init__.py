"""Memory host SDK package — secret, multimodal, engine facades.

Mirrors src/memory-host-sdk/. All modules are barrel re-exports from the
shared SDK package; this provides self-contained stub implementations.
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict


class QmdBinaryAvailability(TypedDict, total=False):
    available: bool
    reason: str | None


def has_configured_memory_secret_input(config: Any) -> bool:
    """Check if a memory secret input is configured."""
    if not isinstance(config, Mapping):
        return False
    secret = config.get("secret") or config.get("secretInput")
    if secret is None:
        return False
    if isinstance(secret, str):
        return bool(secret.strip())
    if isinstance(secret, Mapping):
        return bool(secret.get("value") or secret.get("env"))
    return True


def resolve_memory_secret_input_string(config: Any) -> str | None:
    """Resolve the memory secret input to a string value."""
    if not isinstance(config, Mapping):
        return None
    secret = config.get("secret") or config.get("secretInput")
    if isinstance(secret, str):
        s = secret.strip()
        return s or None
    if isinstance(secret, Mapping):
        value = secret.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def check_qmd_binary_availability() -> QmdBinaryAvailability:
    """Check if the qmd binary is available. Stub — returns unavailable."""
    return {"available": False, "reason": "not_installed"}


def resolve_qmd_binary_unavailable_reason(
    availability: QmdBinaryAvailability,
) -> str | None:
    """Resolve the reason a qmd binary is unavailable."""
    if availability.get("available"):
        return None
    return availability.get("reason")
