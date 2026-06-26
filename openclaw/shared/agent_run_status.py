"""Shared agent-run status predicates for gateway wait loops and delivery announcements.

Mirrors src/shared/agent-run-status.ts.
"""

from __future__ import annotations

from typing import Any

NON_TERMINAL_AGENT_RUN_STATUSES = frozenset({"accepted", "started", "in_flight"})


def is_non_terminal_agent_run_status(status: Any) -> bool:
    """Return True for agent-run statuses that still need polling or live updates."""
    return isinstance(status, str) and status in NON_TERMINAL_AGENT_RUN_STATUSES
