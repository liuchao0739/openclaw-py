"""Runtime maintenance config reads current config and falls back for narrow helpers/tests."""

from __future__ import annotations

from typing import Any


def resolve_maintenance_config() -> dict[str, Any]:
    """Resolve session maintenance config from runtime config with fallback."""
    maintenance: dict[str, Any] | None = None
    try:
        from openclaw.config.config import get_runtime_config

        session = get_runtime_config().get("session", {})
        if isinstance(session, dict):
            maintenance = session.get("maintenance")
    except Exception:
        pass

    if not isinstance(maintenance, dict):
        maintenance = {}

    return {
        "enabled": maintenance.get("enabled", False),
        "maxAgeHours": maintenance.get("maxAgeHours", 168),
        "maxEntries": maintenance.get("maxEntries", 1000),
        "archiveDir": maintenance.get("archiveDir"),
    }
