"""Tests for ACPX register runtime service."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw.acp.runtime import (
    get_acp_runtime_backend,
    register_acp_runtime_backend,
    reset_acp_backends_for_tests,
    unregister_acp_runtime_backend,
)
from openclaw_extensions.acpx import register_runtime


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_acp_backends_for_tests()
    register_runtime._service_module = None
    yield
    reset_acp_backends_for_tests()
    register_runtime._service_module = None


@pytest.fixture
def previous_skip_runtime() -> str | None:
    return os.environ.get("OPENCLAW_SKIP_ACPX_RUNTIME")


@pytest.fixture(autouse=True)
def _restore_skip_env(previous_skip_runtime: str | None) -> None:
    yield
    if previous_skip_runtime is None:
        os.environ.pop("OPENCLAW_SKIP_ACPX_RUNTIME", None)
    else:
        os.environ["OPENCLAW_SKIP_ACPX_RUNTIME"] = previous_skip_runtime


def _create_service_context() -> SimpleNamespace:
    return SimpleNamespace(
        workspace_dir="/tmp/openclaw-acpx-register-test",
        state_dir="/tmp/openclaw-acpx-register-test/state",
        config={},
        logger=SimpleNamespace(
            info=MagicMock(),
            warn=MagicMock(),
            error=MagicMock(),
            debug=MagicMock(),
        ),
    )


class _MockRuntime:
    async def ensure_session(self, input: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": "acpx",
            "runtimeSessionName": input["sessionKey"],
            "sessionKey": input["sessionKey"],
        }

    async def run_turn(self, _input: dict[str, Any]):
        if False:
            yield {}

    async def cancel(self, _input: Any = None) -> None:
        return None

    async def close(self, _input: Any = None) -> None:
        return None

    def is_healthy(self) -> bool:
        return True

    async def probe_availability(self) -> None:
        return None


@pytest.mark.asyncio
async def test_registers_backend_at_startup_and_starts_real_service_on_first_use(
    monkeypatch: pytest.MonkeyPatch,
):
    os.environ.pop("OPENCLAW_SKIP_ACPX_RUNTIME", None)
    real_runtime = _MockRuntime()
    real_service_start = AsyncMock(
        side_effect=lambda ctx: register_acp_runtime_backend(
            "acpx",
            {"runtime": real_runtime},
        )
    )
    real_service_stop = AsyncMock(side_effect=lambda _ctx: unregister_acp_runtime_backend("acpx"))
    create_real_service = MagicMock(
        return_value={
            "id": "real-acpx-runtime",
            "start": real_service_start,
            "stop": real_service_stop,
        }
    )

    service_module = SimpleNamespace(create_acpx_runtime_service=create_real_service)
    monkeypatch.setattr(register_runtime, "_load_service_module", lambda: service_module)

    ctx = _create_service_context()
    service = register_runtime.create_acpx_runtime_service({"pluginConfig": {"timeoutSeconds": 10}})

    await service["start"](ctx)

    backend = get_acp_runtime_backend("acpx")
    assert backend is not None
    deferred_runtime = backend["runtime"]
    assert deferred_runtime is not None
    assert create_real_service.call_count == 0
    assert real_service_start.await_count == 0

    session = await deferred_runtime.ensure_session(
        {
            "sessionKey": "agent:codex:acp:test",
            "agent": "codex",
            "mode": "oneshot",
        }
    )
    assert session == {
        "backend": "acpx",
        "runtimeSessionName": "agent:codex:acp:test",
        "sessionKey": "agent:codex:acp:test",
    }

    create_real_service.assert_called_once_with({"pluginConfig": {"timeoutSeconds": 10}})
    real_service_start.assert_awaited_once_with(ctx)
    assert get_acp_runtime_backend("acpx")["runtime"] is real_runtime
    ctx.logger.info.assert_called_once_with("embedded acpx runtime backend registered lazily")

    turn = deferred_runtime.start_turn(
        {
            "handle": {
                "sessionKey": "agent:codex:acp:test",
                "backend": "acpx",
                "runtimeSessionName": "agent:codex:acp:test",
            },
            "text": "hello",
            "mode": "prompt",
            "requestId": "turn-1",
        }
    )
    result = await turn["result"]
    assert result == {
        "status": "failed",
        "error": {
            "code": "ACP_TURN_FAILED",
            "message": "ACP turn ended without a terminal done event.",
        },
    }

    await service["stop"](ctx)

    real_service_stop.assert_awaited_once_with(ctx)
    assert get_acp_runtime_backend("acpx") is None


@pytest.mark.asyncio
async def test_keeps_explicit_runtime_skip_env_as_only_outer_startup_skip():
    os.environ["OPENCLAW_SKIP_ACPX_RUNTIME"] = "1"
    create_real_service = MagicMock()
    monkeypatch_service = pytest.MonkeyPatch()
    monkeypatch_service.setattr(
        register_runtime,
        "_load_service_module",
        lambda: SimpleNamespace(create_acpx_runtime_service=create_real_service),
    )
    try:
        ctx = _create_service_context()
        service = register_runtime.create_acpx_runtime_service()
        await service["start"](ctx)

        assert create_real_service.call_count == 0
        assert get_acp_runtime_backend("acpx") is None
        ctx.logger.info.assert_called_once_with(
            "skipping embedded acpx runtime backend (OPENCLAW_SKIP_ACPX_RUNTIME=1)"
        )
    finally:
        monkeypatch_service.undo()
