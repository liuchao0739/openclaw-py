"""Logs redacted failover decisions for embedded-agent attempts."""

from __future__ import annotations

import logging
from typing import Callable, Literal, TypedDict

from openclaw.agents.embedded_agent_error_observation import (
    build_api_error_observation_fields,
    sanitize_for_console,
    should_suppress_raw_error_console_suffix,
)
from openclaw.agents.embedded_agent_helpers.types import FailoverReason
from openclaw.agents.embedded_agent_runner.run.auth_profile_failure_policy import (
    AuthProfileFailureReason,
)

_log = logging.getLogger("openclaw.embedded_agent_runner")

FailoverDecision = Literal["rotate_profile", "fallback_model", "surface_error"]
FailoverStage = Literal["prompt", "assistant"]


class FailoverDecisionLoggerInput(TypedDict, total=False):
    stage: FailoverStage
    decision: FailoverDecision
    runId: str
    rawError: str
    failoverReason: FailoverReason | None
    profileFailureReason: AuthProfileFailureReason | None
    provider: str
    model: str
    sourceProvider: str
    sourceModel: str
    profileId: str
    fallbackConfigured: bool
    timedOut: bool
    aborted: bool
    status: int


class FailoverDecisionLoggerBase(TypedDict, total=False):
    stage: FailoverStage
    runId: str
    rawError: str
    failoverReason: FailoverReason | None
    profileFailureReason: AuthProfileFailureReason | None
    provider: str
    model: str
    sourceProvider: str
    sourceModel: str
    profileId: str
    fallbackConfigured: bool
    timedOut: bool
    aborted: bool


def _redact_identifier(value: str, *, length: int = 12) -> str:
    if len(value) <= length:
        return value
    return value[: length // 2] + "…" + value[-(length // 2) :]


def normalize_failover_decision_observation_base(
    base: FailoverDecisionLoggerBase,
) -> FailoverDecisionLoggerBase:
    out = dict(base)
    if out.get("failoverReason") is None and out.get("timedOut"):
        out["failoverReason"] = "timeout"
    if out.get("profileFailureReason") is None and out.get("timedOut"):
        out["profileFailureReason"] = "timeout"
    return out  # type: ignore[return-value]


def create_failover_decision_logger(
    base: FailoverDecisionLoggerBase,
) -> Callable[[FailoverDecision, dict | None], None]:
    normalized = normalize_failover_decision_observation_base(base)
    profile_id = normalized.get("profileId")
    safe_profile_id = _redact_identifier(profile_id, length=12) if profile_id else None
    safe_run_id = sanitize_for_console(normalized.get("runId")) or "-"
    safe_provider = sanitize_for_console(normalized.get("provider")) or "-"
    safe_model = sanitize_for_console(normalized.get("model")) or "-"
    safe_source_provider = sanitize_for_console(normalized.get("sourceProvider")) or safe_provider
    safe_source_model = sanitize_for_console(normalized.get("sourceModel")) or safe_model
    profile_text = safe_profile_id or "-"
    reason_text = normalized.get("failoverReason") or "none"
    source_changed = safe_source_provider != safe_provider or safe_source_model != safe_model

    def log_decision(
        decision: FailoverDecision,
        extra: dict | None = None,
    ) -> None:
        extra = extra or {}
        observed = build_api_error_observation_fields(normalized.get("rawError"))
        safe_preview = sanitize_for_console(observed.get("rawErrorPreview"))
        kind = observed.get("providerRuntimeFailureKind")
        raw_suffix = ""
        if safe_preview and not should_suppress_raw_error_console_suffix(kind):
            raw_suffix = f" rawError={safe_preview}"
        to_suffix = (
            f" to={safe_provider}/{safe_model}" if source_changed else ""
        )
        console = (
            f"embedded run failover decision: runId={safe_run_id} "
            f"stage={normalized.get('stage')} decision={decision} "
            f"reason={reason_text} from={safe_source_provider}/{safe_source_model}"
            f"{to_suffix} profile={profile_text}{raw_suffix}"
        )
        _log.warning(
            "embedded run failover decision",
            extra={
                "event": "embedded_run_failover_decision",
                "runId": normalized.get("runId"),
                "stage": normalized.get("stage"),
                "decision": decision,
                "failoverReason": normalized.get("failoverReason"),
                "profileFailureReason": normalized.get("profileFailureReason"),
                "provider": normalized.get("provider"),
                "model": normalized.get("model"),
                "status": extra.get("status"),
                "consoleMessage": console,
            },
        )

    return log_decision