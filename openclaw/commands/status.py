"""Status command barrel — exposes command and summary builder."""

from __future__ import annotations

from typing import Any


async def status_command(opts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run status command. Deferred to status.command module."""
    return {"ok": False, "error": "status_command not yet ported"}


def get_status_summary(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Get status summary. Deferred to status.summary module."""
    return {"ok": False, "error": "get_status_summary not yet ported"}
