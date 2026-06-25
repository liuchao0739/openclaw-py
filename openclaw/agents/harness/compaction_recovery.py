"""Native harness compaction recovery helpers.

CLI compaction uses these guards to recognize thread-binding failures that can
fall back to context-engine compaction after clearing stale session bindings.
"""

from __future__ import annotations

from typing import Any


def is_recoverable_native_harness_binding_reason(reason: Any) -> bool:
    """Return whether a native harness failure reason indicates a recoverable binding issue."""
    if not isinstance(reason, str):
        return False
    normalized = reason.strip().lower()
    return (
        normalized == "missing_thread_binding"
        or normalized == "stale_thread_binding"
        or "thread not found" in normalized
        or "no thread binding" in normalized
    )


def is_recoverable_native_harness_binding_failure(
    result: dict[str, Any] | None,
) -> bool:
    """Return whether a compact result failed due to a recoverable native binding issue."""
    if result is None or result.get("ok") is not False:
        return False
    failure = result.get("failure")
    failure_reason = failure.get("reason") if isinstance(failure, dict) else None
    return (
        is_recoverable_native_harness_binding_reason(failure_reason)
        or is_recoverable_native_harness_binding_reason(result.get("reason"))
    )
