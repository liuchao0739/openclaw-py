"""Shared helpers for ACPX extension tests."""

from __future__ import annotations

import time
from typing import Any


class InMemoryPluginStateKeyedStore:
    def __init__(self, *, namespace: str, max_entries: int) -> None:
        self.namespace = namespace
        self.max_entries = max_entries
        self._entries: dict[str, dict[str, Any]] = {}

    async def register(
        self,
        key: str,
        value: Any,
        *,
        ttl_ms: int | None = None,
    ) -> None:
        expires_at = int(time.time() * 1000) + ttl_ms if ttl_ms is not None else None
        self._entries[key] = {
            "key": key,
            "value": value,
            "createdAt": int(time.time() * 1000),
            "expiresAt": expires_at,
        }

    async def register_if_absent(
        self,
        key: str,
        value: Any,
        *,
        ttl_ms: int | None = None,
    ) -> bool:
        if key in self._entries:
            return False
        await self.register(key, value, ttl_ms=ttl_ms)
        return True

    async def lookup(self, key: str) -> Any:
        entry = self._entries.get(key)
        return entry["value"] if entry else None

    async def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    async def entries(self) -> list[dict[str, Any]]:
        return list(self._entries.values())

    async def clear(self) -> None:
        self._entries.clear()


_STORES: dict[tuple[str, str], InMemoryPluginStateKeyedStore] = {}


def reset_plugin_state_store_for_tests() -> None:
    _STORES.clear()


def create_plugin_state_keyed_store_for_tests(
    plugin_id: str,
    options: dict[str, Any],
) -> InMemoryPluginStateKeyedStore:
    namespace = options["namespace"]
    key = (plugin_id, namespace)
    existing = _STORES.get(key)
    if existing is not None:
        return existing
    max_entries = options.get("maxEntries", options.get("max_entries", 4096))
    store = InMemoryPluginStateKeyedStore(namespace=namespace, max_entries=max_entries)
    _STORES[key] = store
    return store
