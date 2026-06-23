"""Docker network mode safety helpers."""

from __future__ import annotations

from typing import Literal

NetworkModeBlockReason = Literal["host", "container_namespace_join"]


def normalize_network_mode(network: str | None) -> str | None:
    if network is None:
        return None
    normalized = network.strip().lower()
    return normalized or None


def get_blocked_network_mode_reason(
    *,
    network: str | None,
    allow_container_namespace_join: bool = False,
) -> NetworkModeBlockReason | None:
    normalized = normalize_network_mode(network)
    if not normalized:
        return None
    if normalized == "host":
        return "host"
    if normalized.startswith("container:") and not allow_container_namespace_join:
        return "container_namespace_join"
    return None


def is_dangerous_network_mode(network: str | None) -> bool:
    normalized = normalize_network_mode(network)
    return normalized == "host" or (normalized or "").startswith("container:")