"""Codex app-server extension runner.

Harness integration uses this to let registered extensions observe and adjust
tool results before they are returned to the agent runtime.

The extension factory registry is resolved lazily; when unavailable the runner
operates with no handlers.
"""

from __future__ import annotations

from typing import Any


def _list_codex_app_server_extension_factories() -> list[Any]:
    try:
        from openclaw.plugins.codex_app_server_extension_factory import (
            list_codex_app_server_extension_factories,
        )

        return list_codex_app_server_extension_factories()
    except Exception:
        return []


def create_codex_app_server_tool_result_extension_runner(
    ctx: dict[str, Any],
    factories: list[Any] | None = None,
) -> Any:
    """Create a runner that applies registered Codex app-server tool-result extensions."""
    if factories is None:
        factories = _list_codex_app_server_extension_factories()

    handlers: list[Any] = []

    class _Runtime:
        def on(self, event: str, handler: Any) -> None:
            if event == "tool_result":
                handlers.append(handler)

    runtime = _Runtime()

    import asyncio

    async def _init() -> None:
        for factory in factories:
            await factory(runtime)

    init_promise = _init()

    class _ExtensionRunner:
        async def apply_tool_result_extensions(self, event: dict[str, Any]) -> Any:
            await init_promise
            current = event["result"]
            for handler in handlers:
                try:
                    next_result = await handler({**event, "result": current}, ctx)
                    if next_result and next_result.get("result") is not None:
                        current = next_result["result"]
                except Exception:
                    pass
            return current

    return _ExtensionRunner()
