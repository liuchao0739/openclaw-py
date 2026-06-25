"""Cron doctor migration for managed memory dreaming jobs.

Rewrites legacy dreaming cron jobs to the isolated light-context agent-turn shape.
"""

from __future__ import annotations

from typing import Any

# Constants from memory-host-sdk/dreaming (defined locally until that module is ported)
MANAGED_MEMORY_DREAMING_CRON_NAME = "memory-dreaming"
MANAGED_MEMORY_DREAMING_CRON_TAG = "[managed:memory-dreaming]"
MEMORY_DREAMING_SYSTEM_EVENT_TEXT = "system:memory-dreaming"


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _normalize_optional_lowercase_string(value: Any) -> str | None:
    s = _normalize_optional_string(value)
    return s.lower() if s else None


def _is_managed_dreaming_job(raw: dict[str, Any]) -> bool:
    """Check if a cron job is a managed memory dreaming job."""
    description = _normalize_optional_string(raw.get("description"))
    if description and MANAGED_MEMORY_DREAMING_CRON_TAG in description:
        return True

    name = _normalize_optional_string(raw.get("name"))
    if name != MANAGED_MEMORY_DREAMING_CRON_NAME:
        return False

    payload = raw.get("payload") or {}
    payload_kind = _normalize_optional_lowercase_string(payload.get("kind"))
    if payload_kind == "systemevent":
        return _normalize_optional_string(payload.get("text")) == MEMORY_DREAMING_SYSTEM_EVENT_TEXT
    if payload_kind == "agentturn":
        return _normalize_optional_string(payload.get("message")) == MEMORY_DREAMING_SYSTEM_EVENT_TEXT
    return False


def _is_stale_dreaming_job(raw: dict[str, Any]) -> bool:
    """Check if a dreaming job needs migration to the new shape."""
    session_target = _normalize_optional_lowercase_string(raw.get("sessionTarget"))
    if session_target != "isolated":
        return True

    payload = raw.get("payload") or {}
    payload_kind = _normalize_optional_lowercase_string(payload.get("kind"))
    if payload_kind != "agentturn":
        return True
    if payload.get("lightContext") is not True:
        return True

    delivery = raw.get("delivery") or {}
    delivery_mode = _normalize_optional_lowercase_string(delivery.get("mode"))
    if delivery_mode != "none":
        return True

    return False


def _rewrite_dreaming_job_shape(raw: dict[str, Any]) -> None:
    """Rewrite a dreaming job to the isolated light-context agent-turn shape."""
    raw["sessionTarget"] = "isolated"
    raw["payload"] = {
        "kind": "agentTurn",
        "message": MEMORY_DREAMING_SYSTEM_EVENT_TEXT,
        "lightContext": True,
    }
    raw["delivery"] = {"mode": "none"}


def migrate_legacy_dreaming_payload_shape(
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rewrite managed dreaming jobs to the isolated light-context agent-turn shape.

    Returns a dict with 'changed' (bool) and 'rewrittenCount' (int).
    """
    rewritten_count = 0
    for raw in jobs:
        if not _is_managed_dreaming_job(raw):
            continue
        if not _is_stale_dreaming_job(raw):
            continue
        _rewrite_dreaming_job_shape(raw)
        rewritten_count += 1
    return {"changed": rewritten_count > 0, "rewrittenCount": rewritten_count}


def count_stale_dreaming_jobs(jobs: list[dict[str, Any]]) -> int:
    """Count managed dreaming jobs that still need payload/session/delivery migration."""
    count = 0
    for raw in jobs:
        if _is_managed_dreaming_job(raw) and _is_stale_dreaming_job(raw):
            count += 1
    return count
