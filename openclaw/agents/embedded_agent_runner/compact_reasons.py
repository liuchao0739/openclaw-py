"""Normalizes and classifies compaction failure reasons."""

from __future__ import annotations

import re

MAX_COMPACTION_REASON_DETAIL_CHARS = 100

DEFERRED_CONTEXT_ENGINE_COMPACTION_REASON = "deferred to background context-engine maintenance"


def _norm(reason: str) -> str:
    return (reason or "").strip().lower()


def _is_generic_compaction_cancelled(reason: str) -> bool:
    n = _norm(reason)
    return n in ("compaction cancelled", "error: compaction cancelled")


def resolve_compaction_failure_reason(
    *,
    reason: str,
    safeguard_cancel_reason: str | None = None,
) -> str:
    if _is_generic_compaction_cancelled(reason) and safeguard_cancel_reason:
        return safeguard_cancel_reason
    return reason


def classify_compaction_reason(reason: str | None = None) -> str:
    text = _norm(reason or "")
    if not text:
        return "unknown"
    if "nothing to compact" in text or "no real conversation messages" in text:
        return "no_compactable_entries"
    if "below threshold" in text or "already under target" in text:
        return "below_threshold"
    if "already compacted" in text or "already_compacted" in text:
        return "already_compacted_recently"
    if "deferred to background" in text:
        return "deferred_background"
    if "still exceeds target" in text:
        return "live_context_still_exceeds_target"
    if "guard" in text:
        return "guard_blocked"
    if "summary" in text:
        return "summary_failed"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if any(code in text for code in ("400", "401", "403", "429")):
        return "provider_error_4xx"
    if any(code in text for code in ("500", "502", "503", "504")):
        return "provider_error_5xx"
    return "unknown"


def format_unknown_compaction_reason_detail(reason: str | None = None) -> str | None:
    sanitized = re.sub(r"\s+", " ", (reason or "").strip())
    sanitized = re.sub(r"[^A-Za-z0-9._:@/+~-]+", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        return None
    return sanitized[:MAX_COMPACTION_REASON_DETAIL_CHARS]