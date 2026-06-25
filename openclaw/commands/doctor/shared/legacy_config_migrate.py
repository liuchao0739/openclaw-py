"""Validating legacy config migration wrapper used by doctor config flow."""

from __future__ import annotations

from typing import Any


def _apply_legacy_doctor_migrations(raw: Any) -> dict[str, Any]:
    """Apply legacy doctor migrations to raw config.

    Deferred to legacy-config-compat module; returns raw unchanged when unavailable.
    """
    try:
        from openclaw.commands.doctor.shared.legacy_config_compat import (
            apply_legacy_doctor_migrations,
        )

        return apply_legacy_doctor_migrations(raw)
    except Exception:
        if isinstance(raw, dict):
            return {"next": raw, "changes": []}
        return {"next": None, "changes": []}


def migrate_legacy_config(raw: Any) -> dict[str, Any]:
    """Apply legacy migrations and validate the resulting config shape.

    Returns a dict with 'config', 'changes', and optionally 'partiallyValid'.
    """
    result = _apply_legacy_doctor_migrations(raw)
    next_config = result.get("next")
    changes: list[str] = result.get("changes", [])

    if not next_config:
        return {"config": None, "changes": []}

    # Validation deferred to config/validation module
    try:
        from openclaw.config.validation import validate_config_object_with_plugins

        validated = validate_config_object_with_plugins(next_config)
        if not validated.get("ok"):
            changes.append("Migration applied; other validation issues remain — run doctor to review.")
            return {"config": next_config, "changes": changes, "partiallyValid": True}
        return {"config": validated.get("config", next_config), "changes": changes}
    except Exception:
        return {"config": next_config, "changes": changes, "partiallyValid": True}
