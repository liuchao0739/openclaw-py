"""ACP client stub."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AcpClientOptions:
    cwd: str | None = None
    server_command: str = "openclaw-py"
    server_args: list[str] | None = None
    verbose: bool = False


@dataclass
class AcpClientHandle:
    session_id: str
    connected: bool = True


class AcpClient:
    def __init__(self, options: AcpClientOptions | None = None) -> None:
        self.options = options or AcpClientOptions()

    async def connect(self) -> AcpClientHandle:
        return AcpClientHandle(session_id="acp-session-1")

    async def disconnect(self, handle: AcpClientHandle) -> None:
        handle.connected = False
