from __future__ import annotations

from openclaw.plugin_sdk.channel_entry_contract import define_bundled_channel_entry

plugin_entry = define_bundled_channel_entry({
    "id": "googlechat",
    "name": "Google Chat",
    "description": "OpenClaw Google Chat channel plugin",
    "import_meta_url": __file__,
    "plugin": {
        "specifier": "./channel_plugin_api.py",
        "export_name": "googlechat_plugin",
    },
    "secrets": {
        "specifier": "./secret_contract_api.py",
        "export_name": "channel_secrets",
    },
    "runtime": {
        "specifier": "./runtime_api.py",
        "export_name": "set_google_chat_runtime",
    },
})

__all__ = ["plugin_entry"]