"""Codex app-server shared client helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class CodexAppServerClient:
    def __init__(self) -> None:
        self._closed = False
        self._notification_handlers: list[Callable[[dict[str, Any]], None]] = []
        self._request_handlers: list[Callable[[dict[str, Any]], Any]] = []

    async def request(self, _method: str, _params: Any = None, **_: Any) -> Any:
        return {"data": []}

    def add_notification_handler(self, handler: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        self._notification_handlers.append(handler)

        def cleanup() -> None:
            if handler in self._notification_handlers:
                self._notification_handlers.remove(handler)

        return cleanup

    def add_request_handler(self, handler: Callable[[dict[str, Any]], Any]) -> Callable[[], None]:
        self._request_handlers.append(handler)

        def cleanup() -> None:
            if handler in self._request_handlers:
                self._request_handlers.remove(handler)

        return cleanup

    def close(self) -> None:
        self._closed = True


async def create_isolated_codex_app_server_client(**_options: Any) -> CodexAppServerClient:
    return CodexAppServerClient()


async def clear_shared_codex_app_server_client_and_wait() -> None:
    return None
