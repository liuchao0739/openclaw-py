"""Google Chat API module exposes the plugin public contract.

Mirrors extensions/googlechat/directory-contract-api.ts.
"""

from __future__ import annotations

from openclaw_extensions.googlechat.src.channel_adapters import googlechat_directory_adapter

googlechat_directory_contract_plugin = {
    "id": "googlechat",
    "directory": googlechat_directory_adapter,
}

__all__ = ["googlechat_directory_contract_plugin"]
