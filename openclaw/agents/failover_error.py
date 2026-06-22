"""Provider/model failover error classification."""

from __future__ import annotations

from openclaw.agents.embedded_agent_helpers.types import FailoverReason


class FailoverError(Exception):
    def __init__(
        self,
        message: str,
        *,
        reason: FailoverReason,
        provider: str | None = None,
        model: str | None = None,
        profile_id: str | None = None,
        status: int | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause
        self.name = "FailoverError"
        self.reason = reason
        self.provider = provider
        self.model = model
        self.profile_id = profile_id
        self.status = status


def is_failover_error(err: object) -> bool:
    return isinstance(err, FailoverError)


def resolve_failover_status(reason: FailoverReason) -> int:
    if reason in ("auth", "auth_permanent"):
        return 401
    if reason == "rate_limit":
        return 429
    if reason == "billing":
        return 402
    if reason in ("overloaded", "server_error"):
        return 503
    if reason == "timeout":
        return 504
    return 500