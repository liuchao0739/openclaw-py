from __future__ import annotations

import json
from typing import Any

from openclaw.commands.models.shared import apply_default_model_primary_update, update_config


async def models_set_command(
    model_raw: str,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    updated = await update_config(
        lambda cfg, context: apply_default_model_primary_update(
            {"cfg": cfg, "context": context, "modelRaw": model_raw, "field": "model"}
        )
    )

    log_fn = rt.get("log", print)
    agents = updated.get("agents", {}) if isinstance(updated, dict) else {}
    defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
    model = defaults.get("model") if isinstance(defaults, dict) else None
    if isinstance(model, dict):
        primary = model.get("primary", model_raw)
    else:
        primary = model_raw

    if log_fn:
        log_fn(f"Default model: {primary}")

    return {"ok": True, "model": primary}
