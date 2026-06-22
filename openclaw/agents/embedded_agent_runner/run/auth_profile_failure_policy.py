"""Resolves why an auth profile failed during provider auth selection."""

from __future__ import annotations

from openclaw.agents.embedded_agent_helpers.types import FailoverReason
from openclaw.agents.embedded_agent_runner.run.auth_profile_failure_policy_types import (
    AuthProfileFailurePolicy,
)

AuthProfileFailureReason = FailoverReason


def resolve_auth_profile_failure_reason(
    *,
    failover_reason: FailoverReason | None,
    provider_started: bool | None = None,
    transient_rate_limit: bool | None = None,
    policy: AuthProfileFailurePolicy | None = None,
) -> AuthProfileFailureReason | None:
    if (
        policy == "local"
        or not failover_reason
        or (
            policy == "local_transient"
            and (
                failover_reason == "overloaded"
                or (failover_reason == "rate_limit" and transient_rate_limit is True)
            )
        )
        or failover_reason in ("server_error", "empty_response", "format")
    ):
        return None
    if failover_reason == "timeout" and provider_started is not True:
        return None
    return failover_reason