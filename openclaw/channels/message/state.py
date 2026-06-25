"""Durable outbound message recovery state.

Creates and classifies persisted send records after delivery interruptions.
"""

from __future__ import annotations

import time
from typing import Any, Literal

DurableMessageSendState = Literal["pending", "sent", "suppressed", "failed", "unknown_after_send"]


def create_durable_message_state_record(
    intent: dict[str, Any],
    state: DurableMessageSendState | None = None,
    receipt: dict[str, Any] | None = None,
    updated_at: int | None = None,
    error: Any = None,
) -> dict[str, Any]:
    """Create a durable message recovery record from intent, receipt, and optional error state."""
    record: dict[str, Any] = {
        "intent": intent,
        "state": state or ("sent" if receipt else "pending"),
        "updatedAt": updated_at or int(time.time() * 1000),
    }
    if receipt:
        record["receipt"] = receipt
    if error is not None:
        record["errorMessage"] = str(error) if not isinstance(error, Exception) else str(error)
    return record


def classify_durable_send_recovery_state(
    has_intent: bool = False,
    has_receipt: bool = False,
    platform_send_may_have_started: bool = False,
    failed: bool = False,
    suppressed: bool = False,
) -> DurableMessageSendState:
    """Classify recovery state from persisted intent/receipt facts after a send interruption."""
    if failed:
        return "failed"
    if suppressed:
        return "suppressed"
    if has_receipt:
        return "sent"
    if has_intent and platform_send_may_have_started:
        return "unknown_after_send"
    return "pending"
