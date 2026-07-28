from __future__ import annotations

from openclaw.plugin_sdk.channel_entry_contract import define_bundled_channel_setup_entry

setup_entry = define_bundled_channel_setup_entry({
    "import_meta_url": __file__,
    "plugin": {
        "specifier": "./setup_plugin_api.py",
        "export_name": "googlechat_setup_plugin",
    },
    "secrets": {
        "specifier": "./secret_contract_api.py",
        "export_name": "channel_secrets",
    },
})

__all__ = ["setup_entry"]