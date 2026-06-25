"""Dispatch result helpers for channel turns."""

from __future__ import annotations

from typing import Any, Literal

DispatchOutcome = Literal["delivered", "suppressed", "failed", "skipped"]


def create_dispatch_result(
    outcome: DispatchOutcome,
    *,
    receipt: dict[str, Any] | None = None,
    error: str | None = None,
    suppressed_reason: str | None = None,
    message_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create a standardized dispatch result."""
    result: dict[str, Any] = {"outcome": outcome}
    if receipt:
        result["receipt"] = receipt
    if error:
        result["error"] = error
    if suppressed_reason:
        result["suppressedReason"] = suppressed_reason
    if message_ids:
        result["messageIds"] = message_ids
    return result


def is_delivered(result: dict[str, Any]) -> bool:
    return result.get("outcome") == "delivered"


def is_suppressed(result: dict[str, Any]) -> bool:
    return result.get("outcome") == "suppressed"


def is_failed(result: dict[str, Any]) -> bool:
    return result.get("outcome") == "failed"


def merge_dispatch_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple dispatch results into a summary."""
    if not results:
        return create_dispatch_result("skipped")

    all_message_ids: list[str] = []
    any_delivered = False
    any_failed = False
    any_suppressed = False
    errors: list[str] = []

    for r in results:
        if is_delivered(r):
            any_delivered = True
            ids = r.get("messageIds", [])
            if isinstance(ids, list):
                all_message_ids.extend(ids)
        elif is_failed(r):
            any_failed = True
            if r.get("error"):
                errors.append(r["error"])
        elif is_suppressed(r):
            any_suppressed = True

    if any_failed and not any_delivered:
        return create_dispatch_result("failed", error="; ".join(errors) if errors else None)
    if any_delivered:
        return create_dispatch_result("delivered", message_ids=all_message_ids or None)
    if any_suppressed:
        return create_dispatch_result("suppressed")
    return create_dispatch_result("skipped")
