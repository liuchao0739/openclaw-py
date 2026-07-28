from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol, TypeAlias, TypedDict

from openclaw.llm.core import (
    AssistantMessage,
    ImageContent,
    Message,
    Model,
    TextContent,
    Tool,
    ToolCall,
    ToolResultMessage,
    Usage,
)
from openclaw.llm.event_stream import AssistantMessageEvent

StreamFn = Callable[..., Any]

QueueMode = Literal["all", "one-at-a-time"]

ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh", "max"]

ToolExecutionMode = Literal["sequential", "parallel"]


@dataclass
class AgentToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["toolCall"] = "toolCall"


@dataclass
class BeforeToolCallResult:
    block: bool = False
    reason: str | None = None


@dataclass
class BeforeToolCallContext:
    assistantMessage: AssistantMessage
    toolCall: AgentToolCall
    args: Any
    context: "AgentContext"


@dataclass
class AfterToolCallContext:
    assistantMessage: AssistantMessage
    toolCall: AgentToolCall
    args: Any
    result: "AgentToolResult"
    isError: bool
    context: "AgentContext"


@dataclass
class AfterToolCallResult:
    content: list[TextContent | ImageContent] | None = None
    details: Any = None
    isError: bool | None = None
    terminate: bool | None = None


@dataclass
class ShouldStopAfterTurnContext:
    message: AssistantMessage
    toolResults: list[ToolResultMessage]
    context: "AgentContext"
    newMessages: list["AgentMessage"]


@dataclass
class PrepareNextTurnContext(ShouldStopAfterTurnContext):
    pass


@dataclass
class AgentLoopTurnUpdate:
    context: "AgentContext" | None = None
    model: Model | None = None
    thinkingLevel: ThinkingLevel | None = None


@dataclass
class AgentBashExecutionMessage:
    role: Literal["bashExecution"] = "bashExecution"
    command: str = ""
    output: str = ""
    exitCode: int | None = None
    cancelled: bool = False
    truncated: bool = False
    fullOutputPath: str | None = None
    timestamp: int = 0
    excludeFromContext: bool = False


@dataclass
class AgentCustomMessage:
    role: Literal["custom"] = "custom"
    customType: str = ""
    content: str | list[TextContent | ImageContent] = ""
    display: bool = False
    details: Any = None
    timestamp: int = 0


@dataclass
class AgentBranchSummaryMessage:
    role: Literal["branchSummary"] = "branchSummary"
    summary: str = ""
    fromId: str = ""
    timestamp: int = 0


@dataclass
class AgentCompactionSummaryMessage:
    role: Literal["compactionSummary"] = "compactionSummary"
    summary: str = ""
    tokensBefore: int = 0
    timestamp: int | str = 0
    tokensAfter: int | None = None
    firstKeptEntryId: str | None = None
    details: Any = None


CustomAgentMessages = (
    AgentBashExecutionMessage
    | AgentCustomMessage
    | AgentBranchSummaryMessage
    | AgentCompactionSummaryMessage
)

AgentMessage: TypeAlias = Message | CustomAgentMessages


@dataclass
class AgentToolProgress:
    text: str
    visibility: Literal["channel"] = "channel"
    privacy: Literal["public"] = "public"
    id: str | None = None


@dataclass
class AgentToolResult:
    content: list[TextContent | ImageContent]
    details: Any = None
    progress: AgentToolProgress | None = None
    terminate: bool = False


AgentToolUpdateCallback = Callable[[AgentToolResult], None]


class AgentTool(Protocol):
    name: str
    description: str
    label: str
    parameters: dict[str, Any]
    prepareArguments: Callable[[Any], dict[str, Any]] | None
    executionMode: ToolExecutionMode | None

    def execute(
        self,
        toolCallId: str,
        params: dict[str, Any],
        signal: Any | None = None,
        onUpdate: AgentToolUpdateCallback | None = None,
    ) -> AgentToolResult: ...


@dataclass
class AgentContext:
    systemPrompt: str
    messages: list[AgentMessage] = field(default_factory=list)
    tools: list[AgentTool] | None = None


@dataclass
class AgentState:
    systemPrompt: str
    model: Model
    thinkingLevel: ThinkingLevel
    _tools: list[AgentTool] = field(default_factory=list)
    _messages: list[AgentMessage] = field(default_factory=list)
    isStreaming: bool = False
    streamingMessage: AgentMessage | None = None
    pendingToolCalls: set[str] = field(default_factory=set)
    errorMessage: str | None = None

    def _get_tools(self) -> list[AgentTool]:
        return self._tools

    def _set_tools(self, tools: list[AgentTool]) -> None:
        self._tools = list(tools)

    def _get_messages(self) -> list[AgentMessage]:
        return self._messages

    def _set_messages(self, messages: list[AgentMessage]) -> None:
        self._messages = list(messages)


AgentEvent: TypeAlias = dict[str, Any]


class AgentLoopConfig(TypedDict, total=False):
    model: Model
    thinkingLevel: ThinkingLevel
    reasoning: str | None
    sessionId: str | None
    onPayload: Callable[[Any], Any] | None
    onResponse: Callable[[Any], Any] | None
    transport: str | None
    thinkingBudgets: dict[str, int] | None
    maxRetryDelayMs: int | None
    toolExecution: ToolExecutionMode
    convertToLlm: Callable[[list[AgentMessage]], list[Message]]
    transformContext: Callable[..., Any] | None
    getApiKey: Callable[[str], str | None] | None
    beforeToolCall: Callable[..., Any] | None
    resolveDeferredTool: Callable[..., AgentTool | None] | None
    afterToolCall: Callable[..., Any] | None
    prepareNextTurn: Callable[..., AgentLoopTurnUpdate | None] | None
    shouldStopAfterTurn: Callable[[ShouldStopAfterTurnContext], bool] | None
    getSteeringMessages: Callable[[], list[AgentMessage]] | None
    getFollowUpMessages: Callable[[], list[AgentMessage]] | None
    apiKey: str | None
