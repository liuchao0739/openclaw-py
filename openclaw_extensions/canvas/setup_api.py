"""Canvas setup entrypoint that exposes config migrations."""

from __future__ import annotations

import importlib

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry


def _register(api: OpenClawPluginApi) -> None:
    config_migration = importlib.import_module(
        "openclaw_extensions.canvas.src.config_migration"
    )

    api.register_config_migration(  # type: ignore[attr-defined]
        lambda config: config_migration.migrate_legacy_canvas_host_config(config)
    )


default = define_plugin_entry(
    id="canvas",
    name="Canvas Setup",
    description="Lightweight Canvas setup hooks",
    register=_register,
)
