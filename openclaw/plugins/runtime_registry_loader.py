from __future__ import annotations

from typing import Any


def build_runtime_registry_loader(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "registry": {},
        "loaded": False,
    }


def load_runtime_registry(
    loader: dict[str, Any],
    plugins: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loader["registry"] = plugins or {}
    loader["loaded"] = True
    return loader
