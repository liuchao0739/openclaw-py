from __future__ import annotations

import json
import os
from typing import Any


def _discover_providers() -> list[dict[str, Any]]:
    providers = [
        {
            "id": "openclaw",
            "name": "OpenClaw",
            "description": "OpenClaw native provider",
            "supported": True,
        },
        {
            "id": "claude",
            "name": "Claude",
            "description": "Anthropic Claude provider",
            "supported": True,
        },
        {
            "id": "codex",
            "name": "Codex",
            "description": "Codex provider",
            "supported": True,
        },
        {
            "id": "copilot",
            "name": "Copilot",
            "description": "GitHub Copilot provider",
            "supported": True,
        },
    ]
    return providers


def _read_provider_config(provider_id: str, source: str | None = None) -> dict[str, Any] | None:
    if source:
        source_path = os.path.expanduser(source)
        if os.path.exists(source_path):
            try:
                with open(source_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    return None


async def list_providers(
    source: str | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    providers = _discover_providers()
    for provider in providers:
        config = _read_provider_config(provider["id"], source)
        provider["hasConfig"] = config is not None
    return providers


async def select_provider(
    provider_id: str,
    source: str | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    providers = _discover_providers()
    for provider in providers:
        if provider["id"] == provider_id:
            config = _read_provider_config(provider_id, source)
            return {
                "provider": provider,
                "config": config,
                "supported": True,
            }
    return {
        "provider": {"id": provider_id, "name": provider_id, "description": "Unknown provider"},
        "config": None,
        "supported": False,
    }
