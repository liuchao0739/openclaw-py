"""Public type contract for prepared agent runtime plans."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

AgentRuntimeTransport = Literal["sse", "websocket", "auto"]
AgentRuntimeThinkLevel = Literal[
    "off", "minimal", "low", "medium", "high", "xhigh", "adaptive", "max"
]
AgentRuntimePromptMode = Literal["full", "minimal", "none"]
AgentRuntimePromptTrigger = Literal[
    "cron", "heartbeat", "manual", "memory", "overflow", "user"
]
AgentRuntimeFailoverReason = Literal[
    "auth",
    "auth_permanent",
    "format",
    "rate_limit",
    "overloaded",
    "billing",
    "server_error",
    "timeout",
    "model_not_found",
    "session_expired",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
]


class AgentRuntimeAuthPlan(TypedDict, total=False):
    providerForAuth: str
    authProfileProviderForAuth: str
    harnessAuthProvider: str
    forwardedAuthProfileId: str
    forwardedAuthProfileCandidateIds: list[str]