"""State package — database path helpers.

Mirrors src/state/. Provides path resolution stubs for agent and state databases.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def _resolve_state_sqlite_dir(env: Mapping[str, str] | None = None) -> str:
    """Resolve the OpenClaw state SQLite directory."""
    if env is None:
        env = os.environ
    state_dir = env.get("OPENCLAW_STATE_DIR") or str(Path.home() / ".openclaw")
    return str(Path(state_dir) / "db")


def _normalize_agent_id(agent_id: str) -> str:
    """Normalize an agent ID for path usage."""
    return agent_id.strip().lower().replace(" ", "-") if isinstance(agent_id, str) else "default"


def resolve_openclaw_agent_sqlite_path(
    agent_id: str,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
) -> str:
    """Resolve the SQLite file for one normalized agent id."""
    normalized = _normalize_agent_id(agent_id)
    if path:
        return str(Path(path).resolve())
    return str(
        Path(_resolve_state_sqlite_dir(env)).parent
        / "agents"
        / normalized
        / "agent"
        / "openclaw-agent.sqlite"
    )
