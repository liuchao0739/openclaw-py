from __future__ import annotations

from typing import Any


def build_cli_backend_types() -> dict[str, Any]:
    return {
        "backends": {
            "builtin": "builtin",
            "external": "external",
            "mock": "mock",
        },
        "defaultBackend": "builtin",
    }


def resolve_cli_backend(
    config: dict[str, Any] | None = None,
) -> str:
    config = config or {}
    return config.get("backend", "builtin")
