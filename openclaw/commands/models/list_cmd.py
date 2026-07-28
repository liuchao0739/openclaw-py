from __future__ import annotations

import json
from typing import Any


async def models_list_command(
    opts: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rt = runtime or {}
    options = opts or {}
    json_output = options.get("json", False)

    models = _discover_models()

    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, {"models": models})
        return models

    if rt.get("log"):
        rt["log"](f"\x1b[1mAvailable models:\x1b[22m")
        for model in models:
            provider = model.get("provider", "unknown")
            name = model.get("name", "unknown")
            model_type = model.get("type", "chat")
            rt["log"](f"  {provider}/{name} ({model_type})")

    return models


def _discover_models() -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []

    providers = [
        "anthropic",
        "openai",
        "google",
        "mistral",
        "cohere",
        "groq",
        "qwen",
        "deepseek",
    ]

    for provider in providers:
        models.append({
            "provider": provider,
            "name": f"{provider}-default",
            "type": "chat",
            "supportsImages": False,
            "supportsThinking": False,
        })

    return models
