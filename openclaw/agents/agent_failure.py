from __future__ import annotations

from typing import Any


class AgentFailureReason:
    AUTH = "auth"
    AUTH_PERMANENT = "auth_permanent"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    SESSION_EXPIRED = "session_expired"
    FORMAT = "format"
    EMPTY_RESPONSE = "empty_response"
    NO_ERROR_DETAILS = "no_error_details"
    UNCLASSIFIED = "unclassified"
    UNKNOWN = "unknown"
    SERVER_ERROR = "server_error"


class AgentFailureAction:
    RETRY = "retry"
    FAILOVER = "failover"
    ABORT = "abort"
    WAIT = "wait"


def resolve_agent_failure_strategy(
    reason: str,
    error_count: int = 0,
) -> dict[str, Any]:
    retry_reasons = {"rate_limit", "overloaded", "timeout", "server_error"}
    abort_reasons = {"billing", "auth_permanent", "model_not_found"}

    if reason in abort_reasons:
        return {"action": AgentFailureAction.ABORT, "reason": reason}
    if reason in retry_reasons and error_count < 5:
        return {"action": AgentFailureAction.RETRY, "reason": reason}
    return {"action": AgentFailureAction.FAILOVER, "reason": reason}
