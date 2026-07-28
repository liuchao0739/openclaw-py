from __future__ import annotations

from typing import Any


def build_auth_profile_runtime(
    store: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "store": store or {},
        "config": config or {},
        "state": "idle",
    }


def load_runtime_auth_profiles(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_auth_profile_runtime({}, config)
