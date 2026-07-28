from __future__ import annotations

from typing import Any, AsyncIterator, Literal, Protocol, TypedDict, Union


AcpRuntimePromptMode = Literal["prompt", "steer"]
AcpRuntimeSessionMode = Literal["persistent", "oneshot"]


class AcpSessionUpdateTag(str):
    pass


class AcpRuntimeControl(str):
    pass


class AcpRuntimeHandle(TypedDict):
    sessionKey: str
    backend: str
    runtimeSessionName: str
    cwd: str | None
    acpxRecordId: str | None
    backendSessionId: str | None
    agentSessionId: str | None


class AcpRuntimeEnsureInput(TypedDict, total=False):
    sessionKey: str
    agent: str
    mode: AcpRuntimeSessionMode
    resumeSessionId: str | None
    model: str | None
    thinking: str | None
    cwd: str | None
    env: dict[str, str] | None


class AcpRuntimeTurnAttachment(TypedDict):
    mediaType: str
    data: str


class AcpRuntimeTurnInput(TypedDict):
    handle: AcpRuntimeHandle
    text: str
    attachments: list[AcpRuntimeTurnAttachment] | None
    mode: AcpRuntimePromptMode
    requestId: str
    signal: Any | None


class AcpRuntimeCapabilities(TypedDict, total=False):
    controls: list[AcpRuntimeControl]
    configOptionKeys: list[str] | None


class AcpRuntimeStatus(TypedDict, total=False):
    summary: str | None
    acpxRecordId: str | None
    backendSessionId: str | None
    agentSessionId: str | None
    details: dict[str, Any] | None


class AcpRuntimeDoctorReport(TypedDict):
    ok: bool
    code: str | None
    message: str
    installCommand: str | None
    details: list[str] | None


class _TextDeltaEvent(TypedDict):
    type: Literal["text_delta"]
    text: str
    stream: Literal["output", "thought"] | None
    tag: AcpSessionUpdateTag | None


class _StatusEvent(TypedDict):
    type: Literal["status"]
    text: str
    tag: AcpSessionUpdateTag | None
    used: int | None
    size: int | None


class _ToolCallEvent(TypedDict):
    type: Literal["tool_call"]
    text: str
    tag: AcpSessionUpdateTag | None
    toolCallId: str | None
    status: str | None
    title: str | None


class _DoneEvent(TypedDict):
    type: Literal["done"]
    stopReason: str | None


class _ErrorEvent(TypedDict):
    type: Literal["error"]
    message: str
    code: str | None
    detailCode: str | None
    retryable: bool | None


AcpRuntimeEvent = Union[_TextDeltaEvent, _StatusEvent, _ToolCallEvent, _DoneEvent, _ErrorEvent]


class AcpRuntimeTurnResultError(TypedDict, total=False):
    message: str
    code: str | None
    detailCode: str | None
    retryable: bool | None


class _CompletedResult(TypedDict):
    status: Literal["completed"]
    stopReason: str | None


class _CancelledResult(TypedDict):
    status: Literal["cancelled"]
    stopReason: str | None


class _FailedResult(TypedDict):
    status: Literal["failed"]
    error: AcpRuntimeTurnResultError


AcpRuntimeTurnResult = Union[_CompletedResult, _CancelledResult, _FailedResult]


class AcpRuntimeTurn(Protocol):
    requestId: str
    events: AsyncIterator[AcpRuntimeEvent]

    async def result(self) -> AcpRuntimeTurnResult:
        ...

    async def cancel(self, reason: str | None = None) -> None:
        ...

    async def close_stream(self, reason: str | None = None) -> None:
        ...


class AcpRuntime(Protocol):
    async def ensure_session(self, input: AcpRuntimeEnsureInput) -> AcpRuntimeHandle:
        ...

    async def start_turn(self, input: AcpRuntimeTurnInput) -> AcpRuntimeTurn:
        ...

    async def run_turn(self, input: AcpRuntimeTurnInput) -> AsyncIterator[AcpRuntimeEvent]:
        ...

    async def get_capabilities(
        self, handle: AcpRuntimeHandle | None = None
    ) -> AcpRuntimeCapabilities:
        ...

    async def get_status(
        self, handle: AcpRuntimeHandle, signal: Any | None = None
    ) -> AcpRuntimeStatus:
        ...

    async def set_mode(self, handle: AcpRuntimeHandle, mode: str) -> None:
        ...

    async def set_config_option(
        self, handle: AcpRuntimeHandle, key: str, value: str
    ) -> None:
        ...

    async def doctor(self) -> AcpRuntimeDoctorReport:
        ...

    async def prepare_fresh_session(self, session_key: str) -> None:
        ...

    async def cancel(self, handle: AcpRuntimeHandle, reason: str | None = None) -> None:
        ...

    async def close(
        self,
        handle: AcpRuntimeHandle,
        reason: str,
        discard_persistent_state: bool | None = None,
    ) -> None:
        ...