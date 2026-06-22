"""Public native agent harness contracts (structural typing via TypedDict / Protocol)."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, Protocol, TypedDict, Union

AgentHarnessResultClassification = Literal[
    "ok",
    "error",
    "aborted",
    "compaction",
    "delivery",
    "tool_denied",
    "unknown",
]


class AgentHarnessSupportContext(TypedDict):
    provider: str
    modelId: NotRequired[str]
    requestedRuntime: NotRequired[str]


class AgentHarnessSupportSupported(TypedDict):
    supported: Literal[True]
    priority: NotRequired[int]
    reason: NotRequired[str]


class AgentHarnessSupportUnsupported(TypedDict):
    supported: Literal[False]
    reason: NotRequired[str]


AgentHarnessSupport = Union[AgentHarnessSupportSupported, AgentHarnessSupportUnsupported]


class AgentHarnessDeliveryDefaults(TypedDict, total=False):
    sourceVisibleReplies: Literal["automatic", "message_tool"]


class AgentHarnessSideQuestionResult(TypedDict):
    text: str


class AgentHarnessResetParams(TypedDict, total=False):
    sessionId: str
    sessionKey: str
    sessionFile: str
    reason: Literal["new", "reset", "idle", "daily", "compaction", "deleted", "unknown"]


# Opaque forward refs until embedded run types are fully wired
AgentHarnessAttemptParams = dict[str, Any]
AgentHarnessAttemptResult = dict[str, Any]
AgentHarnessCompactParams = dict[str, Any]
AgentHarnessCompactResult = dict[str, Any]
AgentHarnessSideQuestionParams = dict[str, Any]


class AgentHarness(Protocol):
    id: str
    label: str
    pluginId: NotRequired[str]
    contextEngineHostCapabilities: NotRequired[list[str]]
    deliveryDefaults: NotRequired[AgentHarnessDeliveryDefaults]

    def supports(self, ctx: AgentHarnessSupportContext) -> AgentHarnessSupport: ...

    async def runAttempt(
        self, params: AgentHarnessAttemptParams
    ) -> AgentHarnessAttemptResult: ...

    async def runSideQuestion(
        self, params: AgentHarnessSideQuestionParams
    ) -> AgentHarnessSideQuestionResult: ...

    def classify(
        self,
        result: AgentHarnessAttemptResult,
        ctx: AgentHarnessAttemptParams,
    ) -> AgentHarnessResultClassification | None: ...

    async def compact(
        self, params: AgentHarnessCompactParams
    ) -> AgentHarnessCompactResult | None: ...

    async def reset(self, params: AgentHarnessResetParams) -> None: ...

    async def dispose(self) -> None: ...


class RegisteredAgentHarness(TypedDict):
    harness: Any
    ownerPluginId: NotRequired[str]