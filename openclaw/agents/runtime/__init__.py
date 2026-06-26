"""OpenClaw-owned agent runtime facade and proxy streaming helpers.

Mirrors src/agents/runtime/index.ts. Wires agent-core to the plugin SDK LLM runtime.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from openclaw.agents.runtime.proxy import (
    ProxyStreamOptions,
    build_proxy_request_options,
    process_proxy_event,
    sanitize_proxy_model,
)


# --- Runtime deps bridge ---

class OpenClawAgentCoreRuntime:
    """Runtime deps that bridge agent-core to the plugin SDK LLM runtime."""

    def __init__(self) -> None:
        self._complete_simple: Callable[..., Awaitable[Any]] | None = None
        self._stream_simple: Callable[..., Any] | None = None

    def set_complete_simple(self, fn: Callable[..., Awaitable[Any]]) -> None:
        self._complete_simple = fn

    def set_stream_simple(self, fn: Callable[..., Any]) -> None:
        self._stream_simple = fn

    async def complete_simple(self, *args: Any, **kwargs: Any) -> Any:
        if self._complete_simple is None:
            raise RuntimeError("complete_simple not configured")
        return await self._complete_simple(*args, **kwargs)

    def stream_simple(self, *args: Any, **kwargs: Any) -> Any:
        if self._stream_simple is None:
            raise RuntimeError("stream_simple not configured")
        return self._stream_simple(*args, **kwargs)


openclaw_agent_core_runtime = OpenClawAgentCoreRuntime()


class Agent:
    """OpenClaw agent that uses the plugin SDK LLM runtime."""

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}
        self.runtime = openclaw_agent_core_runtime
        self._system: str | None = None
        self._tools: list[Any] = []
        self._max_turns: int = 0

    @property
    def system(self) -> str | None:
        return self._system

    @system.setter
    def system(self, value: str | None) -> None:
        self._system = value

    @property
    def tools(self) -> list[Any]:
        return self._tools

    def add_tool(self, tool: Any) -> None:
        self._tools.append(tool)

    @property
    def max_turns(self) -> int:
        return self._max_turns

    @max_turns.setter
    def max_turns(self, value: int) -> None:
        self._max_turns = value


__all__ = [
    "ProxyStreamOptions",
    "build_proxy_request_options",
    "process_proxy_event",
    "sanitize_proxy_model",
    "OpenClawAgentCoreRuntime",
    "openclaw_agent_core_runtime",
    "Agent",
]
