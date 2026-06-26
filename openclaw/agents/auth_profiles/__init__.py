"""Auth profiles package — path constants, paths, failure hook, clone.

Mirrors src/agents/auth-profiles/.
"""

from __future__ import annotations

import json
from typing import Any, Callable

AUTH_PROFILE_FILENAME = "auth-profiles.json"
AUTH_STATE_FILENAME = "auth-state.json"
LEGACY_AUTH_FILENAME = "auth.json"


def resolve_auth_store_path(state_dir: str = ".openclaw") -> str:
    return f"{state_dir}/{AUTH_PROFILE_FILENAME}"


def resolve_auth_state_path(state_dir: str = ".openclaw") -> str:
    return f"{state_dir}/{AUTH_STATE_FILENAME}"


def resolve_legacy_auth_store_path(state_dir: str = ".openclaw") -> str:
    return f"{state_dir}/{LEGACY_AUTH_FILENAME}"


def resolve_oauth_refresh_lock_path(state_dir: str = ".openclaw") -> str:
    return f"{state_dir}/oauth-refresh.lock"


def resolve_auth_store_path_for_display(state_dir: str = ".openclaw") -> str:
    return resolve_auth_store_path(state_dir).replace(str.home(), "~") if str else resolve_auth_store_path(state_dir)


def resolve_auth_state_path_for_display(state_dir: str = ".openclaw") -> str:
    return resolve_auth_state_path(state_dir)


# --- Failure hook ---

_auth_profile_failure_hook: Callable[[], None] | None = None


def set_auth_profile_failure_hook(hook: Callable[[], None] | None) -> None:
    global _auth_profile_failure_hook
    _auth_profile_failure_hook = hook


def notify_auth_profile_failure_hook() -> None:
    if _auth_profile_failure_hook:
        _auth_profile_failure_hook()


# --- Clone ---

def clone_auth_profile_store(store: dict[str, Any]) -> dict[str, Any]:
    """Deep-clone an auth profile store, rejecting non-JSON values."""
    def _check(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _check(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_check(v) for v in obj]
        if isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        raise TypeError(f"AuthProfileStore contains non-JSON value: {type(obj).__name__}")

    return _check(store)
