from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict, Union


class JsonObject(dict[str, Any]):
    pass


class GatewayRequestOptions(TypedDict, total=False):
    expectFinal: Optional[bool]
    timeoutMs: Optional[int]


class GatewayEvent(TypedDict, total=False):
    event: str
    payload: Any
    seq: int
    stateVersion: Any


class OpenClawTransport:
    async def request(
        self,
        method: str,
        params: Any = None,
        options: Optional[GatewayRequestOptions] = None,
    ) -> Any:
        ...

    def events(
        self,
        filter: Optional[Any] = None,
    ) -> Any:
        ...

    async def close(self) -> None:
        ...


class ConnectableOpenClawTransport(OpenClawTransport):
    async def connect(self) -> None:
        ...


class RuntimeSelection(TypedDict, total=False):
    type: str
    id: str
    harness: str
    provider: str


class EnvironmentSelection(TypedDict, total=False):
    type: str
    cwd: str
    url: str
    nodeId: str
    repo: str
    ref: str
    provider: str


class EnvironmentSummary(TypedDict, total=False):
    id: str
    type: str
    label: str
    status: str
    capabilities: list[str]


class EnvironmentsListResult(TypedDict):
    environments: list[EnvironmentSummary]


class WorkspaceSelection(TypedDict, total=False):
    cwd: str
    repo: str
    ref: str


ApprovalMode = Literal["ask", "never", "auto", "trusted"]


class ApprovalDecisionParams(TypedDict):
    decision: Literal["allow-once", "allow-always", "deny"]


RunStatus = Literal["accepted", "completed", "failed", "cancelled", "timed_out"]
RunTimestamp = Union[str, int]


class SDKMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str
    toolCallId: str


class ArtifactSummary(TypedDict, total=False):
    id: str
    runId: str
    taskId: str
    sessionId: str
    sessionKey: str
    type: str
    title: str
    mimeType: str
    sizeBytes: int
    messageSeq: int
    source: str
    download: dict[str, str]
    createdAt: str
    expiresAt: str


class ArtifactQuery(TypedDict, total=False):
    sessionKey: str
    runId: str
    taskId: str
    agentId: str


class ArtifactsListResult(TypedDict):
    artifacts: list[ArtifactSummary]


class ArtifactsGetResult(TypedDict):
    artifact: ArtifactSummary


class ArtifactsDownloadResult(TypedDict, total=False):
    artifact: ArtifactSummary
    encoding: str
    data: str
    url: str


TaskStatus = Literal["queued", "running", "completed", "failed", "cancelled", "timed_out"]


class TaskSummary(TypedDict, total=False):
    id: str
    taskId: str
    kind: str
    runtime: str
    status: TaskStatus
    title: str
    agentId: str
    sessionKey: str
    childSessionKey: str
    ownerKey: str
    runId: str
    flowId: str
    parentTaskId: str
    sourceId: str
    createdAt: RunTimestamp
    updatedAt: RunTimestamp
    startedAt: RunTimestamp
    endedAt: RunTimestamp
    progressSummary: str
    terminalSummary: str
    error: str


class TasksListParams(TypedDict, total=False):
    status: Union[TaskStatus, list[TaskStatus]]
    agentId: str
    sessionKey: str
    limit: int
    cursor: str


class TasksListResult(TypedDict, total=False):
    tasks: list[TaskSummary]
    nextCursor: str


class TasksGetResult(TypedDict):
    task: TaskSummary


class TasksCancelResult(TypedDict, total=False):
    found: bool
    cancelled: bool
    reason: str
    task: TaskSummary


class SDKError(TypedDict, total=False):
    code: str
    message: str
    details: Any


class ToolsEffectiveParams(TypedDict):
    sessionKey: str
    agentId: str


class ToolInvokeParams(TypedDict, total=False):
    args: JsonObject
    sessionKey: str
    agentId: str
    confirm: bool
    idempotencyKey: str


class ToolInvokeResult(TypedDict, total=False):
    ok: bool
    toolName: str
    output: Any
    requiresApproval: bool
    approvalId: str
    source: str
    error: SDKError


class RunResult(TypedDict, total=False):
    runId: str
    status: RunStatus
    sessionId: str
    sessionKey: str
    taskId: str
    startedAt: RunTimestamp
    endedAt: RunTimestamp
    output: dict[str, Any]
    usage: dict[str, Any]
    artifacts: list[ArtifactSummary]
    error: SDKError
    raw: Any


OpenClawEventType = Literal[
    "run.created",
    "run.queued",
    "run.started",
    "run.completed",
    "run.failed",
    "run.cancelled",
    "run.timed_out",
    "assistant.delta",
    "assistant.message",
    "thinking.delta",
    "tool.call.started",
    "tool.call.delta",
    "tool.call.completed",
    "tool.call.failed",
    "approval.requested",
    "approval.resolved",
    "question.requested",
    "question.answered",
    "artifact.created",
    "artifact.updated",
    "session.created",
    "session.updated",
    "session.compacted",
    "task.updated",
    "git.branch",
    "git.diff",
    "git.pr",
    "raw",
]


class OpenClawEvent(TypedDict, total=False):
    version: int
    id: str
    ts: int
    type: OpenClawEventType
    runId: str
    sessionId: str
    sessionKey: str
    taskId: str
    agentId: str
    data: Any
    raw: GatewayEvent


class AgentRunParams(TypedDict, total=False):
    input: str
    agentId: str
    model: str
    thinking: str
    sessionId: str
    sessionKey: str
    deliver: bool
    attachments: list[Any]
    timeoutMs: int
    label: str
    runtime: RuntimeSelection
    environment: EnvironmentSelection
    workspace: WorkspaceSelection
    approvals: ApprovalMode
    idempotencyKey: str


class SessionCreateParams(TypedDict, total=False):
    key: str
    agentId: str
    label: str
    model: str
    parentSessionKey: str
    task: str
    message: str


class SessionSendParams(TypedDict):
    key: str
    message: str
    thinking: str
    attachments: list[Any]
    timeoutMs: int
    idempotencyKey: str


class SessionTarget(TypedDict, total=False):
    key: str
    sessionId: str
    agentId: str
    label: str


class AgentsCreateParams(TypedDict):
    name: str
    workspace: str
    model: str
    emoji: str
    avatar: str


class AgentsUpdateParams(TypedDict, total=False):
    agentId: str
    name: str
    workspace: str
    model: str
    emoji: str
    avatar: str


class AgentsDeleteParams(TypedDict):
    agentId: str
    deleteFiles: bool
