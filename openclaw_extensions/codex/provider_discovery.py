"""Static provider discovery entry for Codex."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.codex.provider_catalog import (
    CODEX_APP_SERVER_AUTH_MARKER,
    CODEX_PROVIDER_ID,
    FALLBACK_CODEX_MODELS,
    build_codex_provider_config,
)


def _resolve_codex_plugin_config(ctx: dict[str, Any]) -> Any:
    config = ctx.get("config")
    if not isinstance(config, dict):
        return None
    plugins = config.get("plugins")
    if not isinstance(plugins, dict):
        return None
    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        return None
    codex_entry = entries.get("codex")
    if not isinstance(codex_entry, dict):
        return None
    return codex_entry.get("config")


async def _run_codex_catalog(ctx: dict[str, Any]) -> dict[str, Any]:
    from openclaw_extensions.codex.provider import build_codex_provider_catalog

    return await build_codex_provider_catalog(
        {
            "env": ctx.get("env"),
            "pluginConfig": _resolve_codex_plugin_config(ctx),
        }
    )


async def _static_catalog_run(_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"provider": build_codex_provider_config(FALLBACK_CODEX_MODELS)}


codex_provider_discovery: dict[str, Any] = {
    "id": CODEX_PROVIDER_ID,
    "label": "Codex",
    "docsPath": "/providers/models",
    "auth": [],
    "catalog": {"order": "late", "run": _run_codex_catalog},
    "staticCatalog": {"order": "late", "run": _static_catalog_run},
    "resolveSyntheticAuth": lambda _ctx=None: {
        "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
        "source": "codex-app-server",
        "mode": "token",
    },
}

default = codex_provider_discovery
