from typing import Any, Dict, Optional


class PluginRuntimeStore:
    def __init__(self, plugin_id: str, error_message: str):
        self.plugin_id = plugin_id
        self.error_message = error_message
        self._runtime: Optional[Dict[str, Any]] = None

    def set_runtime(self, runtime: Dict[str, Any]) -> None:
        self._runtime = runtime

    def get_runtime(self) -> Dict[str, Any]:
        if self._runtime is None:
            raise RuntimeError(self.error_message)
        return self._runtime

    def try_get_runtime(self) -> Optional[Dict[str, Any]]:
        return self._runtime


_runtime_store = PluginRuntimeStore("discord", "Discord runtime not initialized")


def set_discord_runtime(runtime: Dict[str, Any]) -> None:
    _runtime_store.set_runtime(runtime)


def get_optional_discord_runtime() -> Optional[Dict[str, Any]]:
    return _runtime_store.try_get_runtime()


def get_discord_runtime() -> Dict[str, Any]:
    return _runtime_store.get_runtime()
