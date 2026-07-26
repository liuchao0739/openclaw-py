"""Lazy ACP runtime proxy for ACPX."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from openclaw_extensions.acpx.src.runtime_turn import lazy_start_runtime_turn


class LazyAcpRuntimeProxy:
    def __init__(self, resolve_runtime: Callable[[], Awaitable[Any]]) -> None:
        self._resolve_runtime = resolve_runtime

    async def ensure_session(self, input: Any) -> Any:
        runtime = await self._resolve_runtime()
        return await runtime.ensure_session(input)

    def start_turn(self, input: Any) -> dict[str, Any]:
        return lazy_start_runtime_turn(self._resolve_runtime, input)

    async def run_turn(self, input: Any):
        runtime = await self._resolve_runtime()
        async for event in runtime.run_turn(input):
            yield event

    async def get_capabilities(self, input: Any) -> dict[str, Any]:
        runtime = await self._resolve_runtime()
        get_capabilities = getattr(runtime, "get_capabilities", None)
        if callable(get_capabilities):
            return await get_capabilities(input)
        return {"controls": []}

    async def get_status(self, input: Any) -> dict[str, Any]:
        runtime = await self._resolve_runtime()
        get_status = getattr(runtime, "get_status", None)
        if callable(get_status):
            return await get_status(input)
        return {}

    async def set_mode(self, input: Any) -> None:
        runtime = await self._resolve_runtime()
        set_mode = getattr(runtime, "set_mode", None)
        if callable(set_mode):
            await set_mode(input)

    async def set_config_option(self, input: Any) -> None:
        runtime = await self._resolve_runtime()
        set_config_option = getattr(runtime, "set_config_option", None)
        if callable(set_config_option):
            await set_config_option(input)

    async def doctor(self) -> dict[str, Any]:
        runtime = await self._resolve_runtime()
        doctor = getattr(runtime, "doctor", None)
        if callable(doctor):
            return await doctor()
        return {"ok": True, "message": "ok"}

    async def prepare_fresh_session(self, input: Any) -> None:
        runtime = await self._resolve_runtime()
        prepare_fresh_session = getattr(runtime, "prepare_fresh_session", None)
        if callable(prepare_fresh_session):
            await prepare_fresh_session(input)

    async def cancel(self, input: Any) -> None:
        runtime = await self._resolve_runtime()
        await runtime.cancel(input)

    async def close(self, input: Any) -> None:
        runtime = await self._resolve_runtime()
        await runtime.close(input)


def create_lazy_acp_runtime_proxy(
    resolve_runtime: Callable[[], Awaitable[Any]],
) -> LazyAcpRuntimeProxy:
    return LazyAcpRuntimeProxy(resolve_runtime)
