from .provider_catalog import (
    CODEX_APP_SERVER_AUTH_MARKER,
    CODEX_PROVIDER_ID,
    FALLBACK_CODEX_MODELS,
    build_codex_provider_config,
)


def _resolve_codex_plugin_config(ctx: dict):
    config = ctx.get("config") or {}
    plugins = config.get("plugins") if isinstance(config, dict) else None
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    codex_entry = entries.get("codex") if isinstance(entries, dict) else None
    if not isinstance(codex_entry, dict):
        return None
    return codex_entry.get("config")


async def _run_codex_catalog(ctx: dict):
    from .provider import build_codex_provider_catalog

    return await build_codex_provider_catalog({
        "env": ctx.get("env"),
        "pluginConfig": _resolve_codex_plugin_config(ctx),
    })


async def _static_catalog_run():
    return {"provider": build_codex_provider_config(FALLBACK_CODEX_MODELS)}


def _resolve_synthetic_auth():
    return {
        "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
        "source": "codex-app-server",
        "mode": "token",
    }


codex_provider_discovery = {
    "id": CODEX_PROVIDER_ID,
    "label": "Codex",
    "docsPath": "/providers/models",
    "auth": [],
    "catalog": {"order": "late", "run": _run_codex_catalog},
    "staticCatalog": {"order": "late", "run": _static_catalog_run},
    "resolveSyntheticAuth": _resolve_synthetic_auth,
}
