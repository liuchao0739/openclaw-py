"""Parses and normalizes persisted cron run-log entry payloads.

Mirrors src/cron/run-log/entry-codec.ts. Parses a persisted cron run-log entry
object and drops invalid or wrong-job rows.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, TypedDict


CRON_FAILOVER_REASONS = frozenset(
    {
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
    }
)

_VALID_DELIVERY_STATUSES = frozenset(
    {"delivered", "not-delivered", "unknown", "not-requested"}
)


class CronRunLogEntry(TypedDict, total=False):
    ts: float
    jobId: str
    action: str
    status: Any
    error: str | None
    errorReason: str | None
    summary: Any
    runId: str | None
    diagnostics: Any
    runAtMs: Any
    durationMs: Any
    nextRunAtMs: Any
    model: str | None
    provider: str | None
    usage: dict[str, Any] | None
    delivered: bool
    deliveryStatus: str
    deliveryError: str
    failureNotificationDelivery: dict[str, Any]
    delivery: dict[str, Any]
    sessionId: str
    sessionKey: str


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def _normalize_cron_run_log_error_reason(value: Any) -> str | None:
    if isinstance(value, str) and value in CRON_FAILOVER_REASONS:
        return value
    return None


def _resolve_failover_reason_from_error(
    error: str | None, provider: str | None
) -> str | None:
    """Best-effort failover reason inference from error text.

    Mirrors the original resolveFailoverReasonFromError heuristics.
    """
    if not error:
        return None
    lowered = error.lower()
    if "401" in lowered or "unauthorized" in lowered or "api key" in lowered:
        return "auth"
    if "403" in lowered or "forbidden" in lowered:
        return "auth_permanent"
    if "429" in lowered or "rate limit" in lowered or "rate_limit" in lowered:
        return "rate_limit"
    if "529" in lowered or "overloaded" in lowered:
        return "overloaded"
    if "402" in lowered or "billing" in lowered or "payment" in lowered:
        return "billing"
    if "500" in lowered or "502" in lowered or "503" in lowered or "server error" in lowered:
        return "server_error"
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "model" in lowered and ("not found" in lowered or "unavailable" in lowered):
        return "model_not_found"
    if "session" in lowered and "expired" in lowered:
        return "session_expired"
    if "empty" in lowered and "response" in lowered:
        return "empty_response"
    return "unknown"


def _normalize_usage(usage: Any) -> dict[str, Any] | None:
    if not isinstance(usage, Mapping):
        return None
    result: dict[str, Any] = {}
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
    ):
        val = usage.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            result[key] = val
    return result or None


def _normalize_diagnostics(value: Any) -> Any:
    """Pass-through diagnostics normalization (deferred full impl)."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    return value


def parse_cron_run_log_entry_object(
    obj: Any,
    opts: Mapping[str, Any] | None = None,
) -> CronRunLogEntry | None:
    """Parse a persisted cron run-log entry object.

    Returns ``None`` for invalid or wrong-job rows.
    """
    job_id_filter = _normalize_optional_string(opts.get("jobId")) if opts else None
    if not isinstance(obj, Mapping):
        return None
    if obj.get("action") != "finished":
        return None
    raw_job_id = obj.get("jobId")
    if not isinstance(raw_job_id, str) or not raw_job_id.strip():
        return None
    ts = obj.get("ts")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool) or math.isnan(ts) or math.isinf(ts):
        return None
    if job_id_filter and raw_job_id != job_id_filter:
        return None

    normalized_error = obj.get("error") if isinstance(obj.get("error"), str) else None
    raw_provider = obj.get("provider")
    normalized_provider = (
        raw_provider if isinstance(raw_provider, str) and raw_provider.strip() else None
    )
    normalized_error_reason = (
        _normalize_cron_run_log_error_reason(obj.get("errorReason"))
        or _resolve_failover_reason_from_error(normalized_error, normalized_provider)
    )

    raw_run_id = obj.get("runId")
    run_id = (
        raw_run_id if isinstance(raw_run_id, str) and raw_run_id.strip() else None
    )
    raw_model = obj.get("model")
    model = raw_model if isinstance(raw_model, str) and raw_model.strip() else None

    entry: CronRunLogEntry = {
        "ts": ts,
        "jobId": raw_job_id,
        "action": "finished",
        "status": obj.get("status"),
        "error": normalized_error,
        "errorReason": normalized_error_reason,
        "summary": obj.get("summary"),
        "runId": run_id,
        "diagnostics": _normalize_diagnostics(obj.get("diagnostics")),
        "runAtMs": obj.get("runAtMs"),
        "durationMs": obj.get("durationMs"),
        "nextRunAtMs": obj.get("nextRunAtMs"),
        "model": model,
        "provider": normalized_provider,
        "usage": _normalize_usage(obj.get("usage")),
    }

    if isinstance(obj.get("delivered"), bool):
        entry["delivered"] = obj["delivered"]
    raw_delivery_status = obj.get("deliveryStatus")
    if isinstance(raw_delivery_status, str) and raw_delivery_status in _VALID_DELIVERY_STATUSES:
        entry["deliveryStatus"] = raw_delivery_status
    if isinstance(obj.get("deliveryError"), str):
        entry["deliveryError"] = obj["deliveryError"]

    fnd = obj.get("failureNotificationDelivery")
    if isinstance(fnd, Mapping):
        fnd_status = fnd.get("status")
        if isinstance(fnd_status, str) and fnd_status in _VALID_DELIVERY_STATUSES:
            fnd_entry: dict[str, Any] = {"status": fnd_status}
            if isinstance(fnd.get("delivered"), bool):
                fnd_entry["delivered"] = fnd["delivered"]
            if isinstance(fnd.get("error"), str):
                fnd_entry["error"] = fnd["error"]
            entry["failureNotificationDelivery"] = fnd_entry

    raw_delivery = obj.get("delivery")
    if isinstance(raw_delivery, Mapping):
        entry["delivery"] = dict(raw_delivery)

    raw_session_id = obj.get("sessionId")
    if isinstance(raw_session_id, str) and raw_session_id.strip():
        entry["sessionId"] = raw_session_id
    raw_session_key = obj.get("sessionKey")
    if isinstance(raw_session_key, str) and raw_session_key.strip():
        entry["sessionKey"] = raw_session_key

    return entry
