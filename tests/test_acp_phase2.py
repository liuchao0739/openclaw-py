"""ACP phase-2 module tests."""

from __future__ import annotations

import pytest

from openclaw.acp.client import AcpClient
from openclaw.acp.control_plane.manager import AcpSessionManager
from openclaw.acp.control_plane.types import AcpCloseSessionInput, AcpInitializeSessionInput, AcpRunTurnInput
from openclaw.acp.runtime.registry import AcpRuntimeBackend, default_registry


@pytest.mark.asyncio
async def test_acp_session_manager_lifecycle() -> None:
    manager = AcpSessionManager()
    status = await manager.initialize_session(
        AcpInitializeSessionInput(sessionKey="s1", agent="main")
    )
    assert status.agent == "main"

    result = await manager.run_turn(
        AcpRunTurnInput(sessionKey="s1", text="hello", requestId="r1")
    )
    assert result["text"] == "hello"

    closed = await manager.close_session(
        AcpCloseSessionInput(sessionKey="s1", reason="done", clearMeta=True)
    )
    assert closed.runtime_closed is True
    assert closed.meta_cleared is True


@pytest.mark.asyncio
async def test_acp_client_connect() -> None:
    client = AcpClient()
    handle = await client.connect()
    assert handle.connected is True
    await client.disconnect(handle)
    assert handle.connected is False


def test_acp_runtime_registry() -> None:
    registry = default_registry
    registry.register(AcpRuntimeBackend(id="codex", label="Codex"))
    assert registry.get("codex") is not None
