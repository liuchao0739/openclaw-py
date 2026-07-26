"""Lazy ACPX runtime service registration."""

from __future__ import annotations

import importlib
import os
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any

from openclaw.acp.runtime import (
    get_acp_runtime_backend,
    register_acp_runtime_backend,
    unregister_acp_runtime_backend,
)
from openclaw_extensions.acpx.src.runtime_proxy import create_lazy_acp_runtime_proxy

ACPX_BACKEND_ID = "acpx"


@dataclass
class _DeferredServiceState:
    ctx: Any | None = None
    params: dict[str, Any] = field(default_factory=dict)
    real_runtime: Any | None = None
    real_service: Any | None = None
    start_promise: Awaitable[Any] | None = None
    _start_task: Any = None


_service_module: Any | None = None


def _load_service_module() -> Any:
    global _service_module
    if _service_module is None:
        _service_module = importlib.import_module("openclaw_extensions.acpx.src.service")
    return _service_module


async def _start_real_service(state: _DeferredServiceState) -> Any:
    if state.real_runtime is not None:
        return state.real_runtime
    if state.ctx is None:
        raise RuntimeError("ACPX runtime service is not started")

    if state._start_task is None:
        async def _run() -> Any:
            service_module = _load_service_module()
            service = service_module.create_acpx_runtime_service(state.params)
            state.real_service = service
            start = service["start"] if isinstance(service, dict) else service.start
            await _maybe_await(start(state.ctx))
            backend = get_acp_runtime_backend(ACPX_BACKEND_ID)
            runtime = backend.get("runtime") if backend else None
            if runtime is None:
                raise RuntimeError("ACPX runtime service did not register an ACP backend")
            state.real_runtime = runtime
            return state.real_runtime

        import asyncio

        state._start_task = asyncio.create_task(_run())

    try:
        return await state._start_task
    except Exception:
        state._start_task = None
        state.real_service = None
        raise


def _create_deferred_runtime(state: _DeferredServiceState) -> Any:
    async def resolve_runtime() -> Any:
        return await _start_real_service(state)

    return create_lazy_acp_runtime_proxy(resolve_runtime)


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


def create_acpx_runtime_service(params: dict[str, Any] | None = None) -> dict[str, Any]:
    state = _DeferredServiceState(params=dict(params or {}))

    async def start(ctx: Any) -> None:
        if os.environ.get("OPENCLAW_SKIP_ACPX_RUNTIME") == "1":
            ctx.logger.info(
                "skipping embedded acpx runtime backend (OPENCLAW_SKIP_ACPX_RUNTIME=1)"
            )
            return

        state.ctx = ctx
        register_acp_runtime_backend(
            ACPX_BACKEND_ID,
            {"runtime": _create_deferred_runtime(state)},
        )
        ctx.logger.info("embedded acpx runtime backend registered lazily")

    async def stop(ctx: Any) -> None:
        if state.real_service is not None:
            stop = (
                state.real_service.get("stop")
                if isinstance(state.real_service, dict)
                else getattr(state.real_service, "stop", None)
            )
            if callable(stop):
                await _maybe_await(stop(ctx))
        else:
            unregister_acp_runtime_backend(ACPX_BACKEND_ID)
        state.ctx = None
        state.real_runtime = None
        state.real_service = None
        state._start_task = None
        state.start_promise = None

    return {
        "id": "acpx-runtime",
        "start": start,
        "stop": stop,
    }
