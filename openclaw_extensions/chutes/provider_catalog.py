"""Chutes provider builders for static and dynamically discovered catalogs."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.chutes.models import (
    CHUTES_BASE_URL,
    CHUTES_MODEL_CATALOG,
    build_chutes_model_definition,
    discover_chutes_models,
)


def build_static_chutes_provider() -> dict[str, Any]:
    return {
        "baseUrl": CHUTES_BASE_URL,
        "api": "openai-completions",
        "models": [build_chutes_model_definition(model) for model in CHUTES_MODEL_CATALOG],
    }


async def build_chutes_provider(access_token: str | None = None) -> dict[str, Any]:
    models = await discover_chutes_models(access_token)
    return {
        "baseUrl": CHUTES_BASE_URL,
        "api": "openai-completions",
        "models": (
            models
            if models
            else [build_chutes_model_definition(model) for model in CHUTES_MODEL_CATALOG]
        ),
    }
