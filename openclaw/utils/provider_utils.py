from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def _resolve_reasoning_output_mode(params: dict) -> str:
    provider = normalize_optional_string(params.get("provider"))
    if not provider:
        return "native"
    try:
        from openclaw.plugins.runtime import resolve_provider_reasoning_output_mode_with_plugin

        plugin_mode = resolve_provider_reasoning_output_mode_with_plugin(
            {
                "provider": provider,
                "config": params.get("config"),
                "workspaceDir": params.get("workspaceDir"),
                "env": params.get("env"),
                "runtimeHandle": params.get("runtimeHandle"),
                "context": {
                    "config": params.get("config"),
                    "workspaceDir": params.get("workspaceDir"),
                    "env": params.get("env"),
                    "provider": provider,
                    "modelId": params.get("modelId"),
                    "modelApi": params.get("modelApi"),
                    "model": params.get("model"),
                },
            }
        )
        if plugin_mode:
            return plugin_mode
    except ImportError:
        pass
    return "native"


def is_reasoning_tag_provider(provider: str | None, options: dict | None = None) -> bool:
    opts = options or {}
    return (
        _resolve_reasoning_output_mode(
            {
                "provider": provider,
                "config": opts.get("config"),
                "workspaceDir": opts.get("workspaceDir"),
                "env": opts.get("env"),
                "modelId": opts.get("modelId"),
                "modelApi": opts.get("modelApi"),
                "model": opts.get("model"),
                "runtimeHandle": opts.get("runtimeHandle"),
            }
        )
        == "tagged"
    )
