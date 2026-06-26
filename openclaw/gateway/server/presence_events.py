"""Presence event helpers broadcast system presence snapshots with synchronized
gateway state versions.

Mirrors src/gateway/server/presence-events.ts.
"""

from __future__ import annotations

from typing import Any, Callable


def _list_system_presence() -> list[Any]:
    """List system presence entries. Stub — returns empty list."""
    return []


def broadcast_presence_snapshot(
    params: dict[str, Any],
) -> int:
    """Broadcast a presence snapshot for gateway clients.

    ``params`` must contain:
    - ``broadcast``: callable(event_type, payload, options)
    - ``increment_presence_version``: callable() -> int
    - ``get_health_version``: callable() -> int

    Returns the new presence version.
    """
    presence_version = params["increment_presence_version"]()
    params["broadcast"](
        "presence",
        {"presence": _list_system_presence()},
        {
            "dropIfSlow": True,
            "stateVersion": {
                "presence": presence_version,
                "health": params["get_health_version"](),
            },
        },
    )
    return presence_version
