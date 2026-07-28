from __future__ import annotations

from typing import Any


def clone_auth_profile_store(store: dict[str, Any]) -> dict[str, Any]:
    def _check(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _check(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_check(v) for v in obj]
        if isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        raise TypeError(f"AuthProfileStore contains non-JSON value: {type(obj).__name__}")

    return _check(store)
