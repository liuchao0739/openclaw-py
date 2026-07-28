from __future__ import annotations

from openclaw.plugin_sdk.runtime_store import create_plugin_runtime_store

_set_runtime, _get_runtime = create_plugin_runtime_store({
    "pluginId": "googlechat",
    "errorMessage": "Google Chat runtime not initialized",
})

set_google_chat_runtime = _set_runtime
get_google_chat_runtime = _get_runtime

__all__ = ["get_google_chat_runtime", "set_google_chat_runtime"]