from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeAlias, Union, runtime_checkable

from openclaw.llm.core import ImageContent, Model, TextContent, Transport

from ..agent_types import (
    AgentEvent,
    AgentMessage,
    AgentTool,
    QueueMode,
    ThinkingLevel,
)

Result: TypeAlias = Union[
    dict[str, Any],
]


def ok(value: Any) -> dict[str, Any]:
    return {"ok": True, "value": value}


def err(error: Any) -> dict[str, Any]:
    return {"ok": False, "error": error}


def to_error(error: Any) -> Exception:
    if isinstance(error, Exception):
        return error
    if isinstance(error, str):
        return Exception(error)
    try:
        return Exception(str(error))
    except Exception:
        return Exception(repr(error))


@dataclass
class Skill:
    name: str
    description: str
    content: str
    filePath: str
    promptVersion: str | None = None
    disableModelInvocation: bool | None = None


@dataclass
class PromptTemplate:
    name: str
    content: str
    description: str | None = None


@dataclass
class AgentHarnessResources:
    promptTemplates: list[PromptTemplate] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)


@dataclass
class AgentHarnessStreamOptions:
    transport: str | None = None
    timeoutMs: int | None = None
    maxRetries: int | None = None
    maxRetryDelayMs: int | None = None
    headers: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None
    cacheRetention: Any | None = None


@dataclass
class AgentHarnessStreamOptionsPatch:
    transport: str | None = None
    timeoutMs: int | None = None
    maxRetries: int | None = None
    maxRetryDelayMs: int | None = None
    headers: dict[str, str | None] | None = None
    metadata: dict[str, Any] | None = None
    cacheRetention: Any | None = None


FileKind: TypeAlias = Literal["file", "directory", "symlink"]
FileErrorCode: TypeAlias = Literal[
    "aborted",
    "not_found",
    "permission_denied",
    "not_directory",
    "is_directory",
    "invalid",
    "not_supported",
    "unknown",
]


class FileError(Exception):
    def __init__(
        self,
        code: FileErrorCode,
        message: str,
        path: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "FileError"
        self.code = code
        self.path = path
        self.cause = cause


ExecutionErrorCode: TypeAlias = Literal[
    "aborted",
    "timeout",
    "shell_unavailable",
    "spawn_error",
    "callback_error",
    "unknown",
]


class ExecutionError(Exception):
    def __init__(
        self,
        code: ExecutionErrorCode,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "ExecutionError"
        self.code = code
        self.cause = cause


CompactionErrorCode: TypeAlias = Literal[
    "aborted",
    "summarization_failed",
    "invalid_session",
    "unknown",
]


class CompactionError(Exception):
    def __init__(
        self,
        code: CompactionErrorCode,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "CompactionError"
        self.code = code
        self.cause = cause


BranchSummaryErrorCode: TypeAlias = Literal[
    "aborted",
    "summarization_failed",
    "invalid_session",
]


class BranchSummaryError(Exception):
    def __init__(
        self,
        code: BranchSummaryErrorCode,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "BranchSummaryError"
        self.code = code
        self.cause = cause


SessionErrorCode: TypeAlias = Literal[
    "not_found",
    "invalid_session",
    "invalid_entry",
    "invalid_fork_target",
    "storage",
    "unknown",
]


class SessionError(Exception):
    def __init__(
        self,
        code: SessionErrorCode,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "SessionError"
        self.code = code
        self.cause = cause


AgentHarnessErrorCode: TypeAlias = Literal[
    "busy",
    "invalid_state",
    "invalid_argument",
    "session",
    "hook",
    "auth",
    "compaction",
    "branch_summary",
    "unknown",
]


class AgentHarnessError(Exception):
    def __init__(
        self,
        code: AgentHarnessErrorCode,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "AgentHarnessError"
        self.code = code
        self.cause = cause


@dataclass
class FileInfo:
    name: str
    path: str
    kind: FileKind
    size: int
    mtimeMs: float


@dataclass
class ExecutionEnvExecOptions:
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout: int | None = None
    abortSignal: Any | None = None
    onStdout: Any | None = None
    onStderr: Any | None = None


@runtime_checkable
class FileSystem(Protocol):
    cwd: str

    async def absolutePath(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def joinPath(self, parts: list[str], abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def readTextFile(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def readTextLines(self, path: str, options: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def readBinaryFile(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def writeFile(self, path: str, content: Any, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def appendFile(self, path: str, content: Any, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def fileInfo(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def listDir(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def canonicalPath(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def exists(self, path: str, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def createDir(self, path: str, options: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def remove(self, path: str, options: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def createTempDir(self, prefix: str | None = None, abortSignal: Any | None = None) -> dict[str, Any]: ...
    async def createTempFile(self, options: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def cleanup(self) -> None: ...


@runtime_checkable
class Shell(Protocol):
    async def exec(
        self,
        command: str,
        options: ExecutionEnvExecOptions | None = None,
    ) -> dict[str, Any]: ...

    async def cleanup(self) -> None: ...


@runtime_checkable
class ExecutionEnv(FileSystem, Shell, Protocol):
    pass


@dataclass
class SessionTreeEntryBase:
    type: str
    id: str
    parentId: str | None
    timestamp: str
    appendMode: Literal["side"] | None = None


@dataclass
class MessageEntry(SessionTreeEntryBase):
    message: AgentMessage = field(default_factory=dict)


@dataclass
class ThinkingLevelChangeEntry(SessionTreeEntryBase):
    thinkingLevel: str = ""


@dataclass
class ModelChangeEntry(SessionTreeEntryBase):
    provider: str = ""
    modelId: str = ""


@dataclass
class CompactionEntry(SessionTreeEntryBase):
    summary: str = ""
    firstKeptEntryId: str = ""
    tokensBefore: int = 0
    details: Any | None = None
    fromHook: bool | None = None


@dataclass
class BranchSummaryEntry(SessionTreeEntryBase):
    fromId: str = ""
    summary: str = ""
    details: Any | None = None
    fromHook: bool | None = None


@dataclass
class CustomEntry(SessionTreeEntryBase):
    customType: str = ""
    data: Any | None = None


@dataclass
class CustomMessageEntry(SessionTreeEntryBase):
    customType: str = ""
    content: Any = None
    details: Any | None = None
    display: bool = False


@dataclass
class LabelEntry(SessionTreeEntryBase):
    targetId: str = ""
    label: str | None = None


@dataclass
class SessionInfoEntry(SessionTreeEntryBase):
    name: str | None = None


@dataclass
class LeafEntry(SessionTreeEntryBase):
    targetId: str | None = None
    appendParentId: str | None = None


SessionTreeEntry: TypeAlias = Union[
    MessageEntry,
    ThinkingLevelChangeEntry,
    ModelChangeEntry,
    CompactionEntry,
    BranchSummaryEntry,
    CustomEntry,
    CustomMessageEntry,
    LabelEntry,
    SessionInfoEntry,
    LeafEntry,
]


@dataclass
class SessionContext:
    messages: list[AgentMessage] = field(default_factory=list)
    thinkingLevel: str = "off"
    model: dict[str, str] | None = None


@dataclass
class SessionMetadata:
    id: str
    createdAt: str


@dataclass
class JsonlSessionMetadata(SessionMetadata):
    cwd: str = ""
    path: str = ""
    parentSessionPath: str | None = None


@runtime_checkable
class SessionStorage(Protocol):
    async def getMetadata(self) -> SessionMetadata: ...
    async def getLeafId(self) -> str | None: ...
    async def getAppendParentId(self) -> str | None: ...
    async def setLeafId(self, leafId: str | None) -> None: ...
    async def createEntryId(self) -> str: ...
    async def appendEntry(self, entry: SessionTreeEntry) -> None: ...
    async def getEntry(self, id: str) -> SessionTreeEntry | None: ...
    async def findEntries(self, type: str) -> list[SessionTreeEntry]: ...
    async def getLabel(self, id: str) -> str | None: ...
    async def getPathToRoot(self, leafId: str | None) -> list[SessionTreeEntry]: ...
    async def getEntries(self) -> list[SessionTreeEntry]: ...


AgentHarnessPhase: TypeAlias = Literal[
    "idle",
    "turn",
    "compaction",
    "branch_summary",
    "retry",
]


@dataclass
class QueueUpdateEvent:
    type: str = "queue_update"
    steer: list[AgentMessage] = field(default_factory=list)
    followUp: list[AgentMessage] = field(default_factory=list)
    nextTurn: list[AgentMessage] = field(default_factory=list)


@dataclass
class SavePointEvent:
    type: str = "save_point"
    hadPendingMutations: bool = False


@dataclass
class AbortEvent:
    type: str = "abort"
    clearedSteer: list[AgentMessage] = field(default_factory=list)
    clearedFollowUp: list[AgentMessage] = field(default_factory=list)


@dataclass
class SettledEvent:
    type: str = "settled"
    nextTurnCount: int = 0


@dataclass
class BeforeAgentStartEvent:
    type: str = "before_agent_start"
    prompt: str = ""
    images: list[ImageContent] | None = None
    systemPrompt: str = ""
    resources: AgentHarnessResources = field(default_factory=AgentHarnessResources)


@dataclass
class ContextEvent:
    type: str = "context"
    messages: list[AgentMessage] = field(default_factory=list)


@dataclass
class BeforeProviderRequestEvent:
    type: str = "before_provider_request"
    model: Model = field(default_factory=Model)
    sessionId: str = ""
    streamOptions: AgentHarnessStreamOptions = field(default_factory=AgentHarnessStreamOptions)


@dataclass
class BeforeProviderPayloadEvent:
    type: str = "before_provider_payload"
    model: Model = field(default_factory=Model)
    payload: Any = None


@dataclass
class AfterProviderResponseEvent:
    type: str = "after_provider_response"
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolCallEvent:
    type: str = "tool_call"
    toolCallId: str = ""
    toolName: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResultEvent:
    type: str = "tool_result"
    toolCallId: str = ""
    toolName: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    content: list[Any] = field(default_factory=list)
    details: Any = None
    isError: bool = False


@dataclass
class SessionBeforeCompactEvent:
    type: str = "session_before_compact"
    preparation: Any = None
    branchEntries: list[SessionTreeEntry] = field(default_factory=list)
    customInstructions: str | None = None
    signal: Any = None


@dataclass
class SessionCompactEvent:
    type: str = "session_compact"
    compactionEntry: CompactionEntry = field(default_factory=CompactionEntry)
    fromHook: bool = False


@dataclass
class SessionBeforeTreeEvent:
    type: str = "session_before_tree"
    preparation: Any = None
    signal: Any = None


@dataclass
class SessionTreeEvent:
    type: str = "session_tree"
    newLeafId: str | None = None
    oldLeafId: str | None = None
    summaryEntry: BranchSummaryEntry | None = None
    fromHook: bool | None = None


@dataclass
class ModelSelectEvent:
    type: str = "model_select"
    model: Model = field(default_factory=Model)
    previousModel: Model | None = None
    source: str = "set"


@dataclass
class ThinkingLevelSelectEvent:
    type: str = "thinking_level_select"
    level: ThinkingLevel = "off"
    previousLevel: ThinkingLevel = "off"


@dataclass
class ResourcesUpdateEvent:
    type: str = "resources_update"
    resources: AgentHarnessResources = field(default_factory=AgentHarnessResources)
    previousResources: AgentHarnessResources = field(default_factory=AgentHarnessResources)


AgentHarnessOwnEvent: TypeAlias = Union[
    QueueUpdateEvent,
    SavePointEvent,
    AbortEvent,
    SettledEvent,
    BeforeAgentStartEvent,
    ContextEvent,
    BeforeProviderRequestEvent,
    BeforeProviderPayloadEvent,
    AfterProviderResponseEvent,
    ToolCallEvent,
    ToolResultEvent,
    SessionBeforeCompactEvent,
    SessionCompactEvent,
    SessionBeforeTreeEvent,
    SessionTreeEvent,
    ModelSelectEvent,
    ThinkingLevelSelectEvent,
    ResourcesUpdateEvent,
]

AgentHarnessEvent: TypeAlias = Union[AgentEvent, AgentHarnessOwnEvent]


@dataclass
class BeforeAgentStartResult:
    messages: list[AgentMessage] | None = None
    systemPrompt: str | None = None


@dataclass
class ContextResult:
    messages: list[AgentMessage] = field(default_factory=list)


@dataclass
class BeforeProviderRequestResult:
    streamOptions: AgentHarnessStreamOptionsPatch | None = None


@dataclass
class BeforeProviderPayloadResult:
    payload: Any = None


@dataclass
class ToolCallResult:
    block: bool | None = None
    reason: str | None = None


@dataclass
class ToolResultPatch:
    content: list[Any] | None = None
    details: Any = None
    isError: bool | None = None
    terminate: bool | None = None


@dataclass
class SessionBeforeCompactResult:
    cancel: bool | None = None
    compaction: Any | None = None


@dataclass
class SessionBeforeTreeResult:
    cancel: bool | None = None
    summary: dict[str, Any] | None = None
    customInstructions: str | None = None
    replaceInstructions: bool | None = None
    label: str | None = None


@dataclass
class AbortResult:
    clearedSteer: list[AgentMessage] = field(default_factory=list)
    clearedFollowUp: list[AgentMessage] = field(default_factory=list)


@dataclass
class CompactResult:
    summary: str = ""
    firstKeptEntryId: str = ""
    tokensBefore: int = 0
    details: Any = None


@dataclass
class NavigateTreeResult:
    cancelled: bool = False
    editorText: str | None = None
    summaryEntry: BranchSummaryEntry | None = None


@dataclass
class CompactionSettings:
    enabled: bool = False
    reserveTokens: int = 0
    keepRecentTokens: int = 0


@dataclass
class FileOperations:
    read: set[str] = field(default_factory=set)
    written: set[str] = field(default_factory=set)
    edited: set[str] = field(default_factory=set)


@dataclass
class CompactionPreparation:
    firstKeptEntryId: str = ""
    messagesToSummarize: list[AgentMessage] = field(default_factory=list)
    turnPrefixMessages: list[AgentMessage] = field(default_factory=list)
    isSplitTurn: bool = False
    tokensBefore: int = 0
    previousSummary: str | None = None
    fileOps: FileOperations = field(default_factory=FileOperations)
    settings: CompactionSettings = field(default_factory=CompactionSettings)


@dataclass
class TreePreparation:
    targetId: str = ""
    oldLeafId: str | None = None
    commonAncestorId: str | None = None
    entriesToSummarize: list[SessionTreeEntry] = field(default_factory=list)
    userWantsSummary: bool = False
    customInstructions: str | None = None
    replaceInstructions: bool | None = None
    label: str | None = None


@dataclass
class GenerateBranchSummaryOptions:
    model: Model = field(default_factory=Model)
    apiKey: str = ""
    headers: dict[str, str] | None = None
    signal: Any = None
    runtime: Any | None = None
    streamFn: Any | None = None
    customInstructions: str | None = None
    replaceInstructions: bool | None = None
    reserveTokens: int | None = None


@dataclass
class BranchSummaryResult:
    summary: str = ""
    readFiles: list[str] = field(default_factory=list)
    modifiedFiles: list[str] = field(default_factory=list)
