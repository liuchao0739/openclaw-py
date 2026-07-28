from __future__ import annotations

from typing import Any


def build_config_activation_shared(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "activated": False,
        "activationSource": None,
    }


def resolve_config_activation(
    config: dict[str, Any],
    activation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    activation = activation or build_config_activation_shared(config)
    return {
        **activation,
        "activated": True,
        "activationSource": "config",
    }
