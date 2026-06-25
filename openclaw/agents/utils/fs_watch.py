"""Filesystem watching helpers.

Deferred until the full fs-watch abstraction is needed.
"""

from __future__ import annotations

from typing import Any


class FsWatcher:
    """Minimal filesystem watcher stub."""

    def __init__(self, paths: list[str] | None = None) -> None:
        self._paths = paths or []
        self._callbacks: list[Any] = []

    def add(self, path: str) -> None:
        self._paths.append(path)

    def on_change(self, callback: Any) -> Any:
        self._callbacks.append(callback)
        return lambda: self._callbacks.remove(callback) if callback in self._callbacks else None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
