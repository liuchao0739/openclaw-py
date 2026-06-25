"""Command for setting the default image model."""

from __future__ import annotations

from typing import Any


async def models_set_image_command(
    model_raw: str,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Set agents.defaults.imageModel.primary after resolving aliases/catalog provider aliases.

    Deferred to config/shared modules; returns a result dict.
    """
    rt = runtime or {}
    try:
        from openclaw.commands.models.shared import apply_default_model_primary_update, update_config

        updated = await update_config(
            lambda cfg: apply_default_model_primary_update(
                {"cfg": cfg, "modelRaw": model_raw, "field": "imageModel"}
            )
        )

        log_fn = rt.get("log", print)
        primary = None
        agents = updated.get("agents", {}) if isinstance(updated, dict) else {}
        defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
        image_model = defaults.get("imageModel")
        if isinstance(image_model, dict):
            primary = image_model.get("primary")

        if log_fn:
            log_fn(f"Image model: {primary or model_raw}")

        return {"ok": True, "model": primary or model_raw}
    except Exception as err:
        return {"ok": False, "error": str(err), "model": model_raw}
