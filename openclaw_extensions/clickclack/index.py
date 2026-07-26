"""Bundled channel entry metadata for the ClickClack plugin."""

from __future__ import annotations

from pathlib import Path

from openclaw.plugin_sdk.channel_entry_contract import define_bundled_channel_entry

default = define_bundled_channel_entry(
    id="clickclack",
    name="ClickClack",
    description="ClickClack channel plugin",
    import_meta_path=Path(__file__),
    plugin={
        "specifier": "./channel-plugin-api.js",
        "export_name": "click_clack_plugin",
    },
    runtime={
        "specifier": "./api.js",
        "export_name": "set_click_clack_runtime",
    },
)
