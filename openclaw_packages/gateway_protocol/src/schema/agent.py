from typing import Literal, Final, Optional, List, Any

AGENT_IDENTITY_KIND = Literal["cli", "external", "native"]

AGENT_IDENTITY_KIND_CLI: Literal["cli"] = "cli"
AGENT_IDENTITY_KIND_EXTERNAL: Literal["external"] = "external"
AGENT_IDENTITY_KIND_NATIVE: Literal["native"] = "native"

AGENT_IDENTITY_KINDS: Final[tuple] = (
    AGENT_IDENTITY_KIND_CLI,
    AGENT_IDENTITY_KIND_EXTERNAL,
    AGENT_IDENTITY_KIND_NATIVE,
)

AGENT_RUN_STATUS = Literal["cancelled", "completed", "failed", "running", "scheduled"]

AGENT_RUN_STATUS_CANCELLED: Literal["cancelled"] = "cancelled"
AGENT_RUN_STATUS_COMPLETED: Literal["completed"] = "completed"
AGENT_RUN_STATUS_FAILED: Literal["failed"] = "failed"
AGENT_RUN_STATUS_RUNNING: Literal["running"] = "running"
AGENT_RUN_STATUS_SCHEDULED: Literal["scheduled"] = "scheduled"

AGENT_RUN_STATUSES: Final[tuple] = (
    AGENT_RUN_STATUS_CANCELLED,
    AGENT_RUN_STATUS_COMPLETED,
    AGENT_RUN_STATUS_FAILED,
    AGENT_RUN_STATUS_RUNNING,
    AGENT_RUN_STATUS_SCHEDULED,
)

class AgentIdentityParams:
    identity_kind: AGENT_IDENTITY_KIND
    name: Optional[str]
    agent_id: Optional[str]
    description: Optional[str]
    version: Optional[str]
    metadata: Optional[dict]

class AgentIdentityResult:
    identity_kind: AGENT_IDENTITY_KIND
    name: Optional[str]
    agent_id: Optional[str]
    description: Optional[str]
    version: Optional[str]
    metadata: Optional[dict]

class AgentParams:
    system_prompt: Optional[str]
    tools: Optional[List[str]]
    model: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    metadata: Optional[dict]

class AgentEvent:
    event: str
    payload: Optional[Any]
    metadata: Optional[dict]

class AgentWaitParams:
    timeout_ms: Optional[int]
    poll_interval_ms: Optional[int]

AgentParamsGetParams = Any
AgentParamsGetResult = Any
AgentParamsUpdateParams = Any
AgentParamsUpdateResult = Any
AgentIdentityGetParams = Any
AgentIdentityGetResult = Any
AgentIdentityUpdateParams = Any
AgentIdentityUpdateResult = Any
AgentSummaryGetParams = Any
AgentSummaryGetResult = Any
AgentWaitGetParams = Any
AgentWaitGetResult = Any
AgentWaitUpdateParams = Any
AgentWaitUpdateResult = Any
AgentEventParams = Any
AgentEventResult = Any
