"""Public Codex Supervisor endpoint, session, and JSON-RPC connection types."""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict


class CodexSupervisorStdioEndpoint(TypedDict, total=False):
    id: str
    label: str
    transport: Literal["stdio-proxy"]
    command: str
    args: list[str]
    cwd: str


class CodexSupervisorWebSocketEndpoint(TypedDict, total=False):
    id: str
    label: str
    transport: Literal["websocket"]
    url: str
    authTokenEnv: str


CodexSupervisorEndpoint = CodexSupervisorStdioEndpoint | CodexSupervisorWebSocketEndpoint

CodexSupervisorTurnMode = Literal["auto", "start", "steer"]

CodexSupervisorThreadStatus = str


class CodexSupervisorSession(TypedDict, total=False):
    endpointId: str
    threadId: str
    sessionId: str
    cwd: str
    preview: str
    name: str | None
    source: str
    status: CodexSupervisorThreadStatus
    updatedAt: int
    humanAttached: bool


class CodexSupervisorSendResult(TypedDict, total=False):
    endpointId: str
    threadId: str
    mode: Literal["start", "steer"]
    turnId: str
    status: str


class CodexJsonRpcConnection(Protocol):
    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any: ...

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None: ...

    async def close(self) -> None: ...


class CodexSupervisorEndpointHealth(TypedDict, total=False):
    endpointId: str
    ok: bool
    detail: str


class CodexSupervisorSessionListResult(TypedDict):
    sessions: list[CodexSupervisorSession]
    errors: list[CodexSupervisorEndpointHealth]
