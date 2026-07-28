from __future__ import annotations

from typing import Any


async def apply_default_model_primary_update(params: dict[str, Any]) -> dict[str, Any]:
    cfg = params.get("cfg", {})
    model_raw = params.get("modelRaw", "")
    field = params.get("field", "model")

    agents = cfg.get("agents", {})
    defaults = agents.get("defaults", {})
    model_config = defaults.get(field, {})

    if not isinstance(model_config, dict):
        model_config = {}

    model_config["primary"] = model_raw
    defaults[field] = model_config
    agents["defaults"] = defaults
    cfg["agents"] = agents

    return cfg


async def update_config(fn: Any) -> dict[str, Any]:
    try:
        from openclaw.config.loader import get_runtime_config
        cfg = get_runtime_config()
    except Exception:
        cfg = {}

    context = {"runtimeConfig": cfg}
    result = fn(cfg, context)
    return result
