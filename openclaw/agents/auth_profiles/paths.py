from __future__ import annotations

from typing import Any


def build_auth_profile_paths(
    state_dir: str = ".openclaw",
    agent_dir: str | None = None,
) -> dict[str, Any]:
    import os
    return {
        "stateDir": state_dir,
        "authStorePath": os.path.join(state_dir, "auth-profiles.json"),
        "authStatePath": os.path.join(state_dir, "auth-state.json"),
        "agentDir": agent_dir,
    }
