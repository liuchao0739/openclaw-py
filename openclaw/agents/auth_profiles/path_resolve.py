from __future__ import annotations

from typing import Any


def resolve_auth_store_path(state_dir: str = ".openclaw") -> str:
    import os
    return os.path.join(state_dir, "auth-profiles.json")


def resolve_auth_state_path(state_dir: str = ".openclaw") -> str:
    import os
    return os.path.join(state_dir, "auth-state.json")


def resolve_legacy_auth_store_path(state_dir: str = ".openclaw") -> str:
    import os
    return os.path.join(state_dir, "oauth.json")
