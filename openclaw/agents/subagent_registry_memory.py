"""Process-local live subagent run map.

Shared by registry read/write helpers for active in-memory run state.
"""

from __future__ import annotations

from typing import Any

# Process-local map of subagent run records keyed by run id
subagent_runs: dict[str, dict[str, Any]] = {}


def clear_subagent_runs() -> None:
    """Clear all in-memory subagent run records."""
    subagent_runs.clear()


def get_subagent_run(run_id: str) -> dict[str, Any] | None:
    """Get a subagent run record by id."""
    return subagent_runs.get(run_id)


def set_subagent_run(run_id: str, record: dict[str, Any]) -> None:
    """Set a subagent run record."""
    subagent_runs[run_id] = record


def remove_subagent_run(run_id: str) -> None:
    """Remove a subagent run record."""
    subagent_runs.pop(run_id, None)
