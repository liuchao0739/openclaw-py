"""Resolves create-time default delivery for new cron jobs.

Mirrors src/cron/service/initial-delivery.ts.
"""

from __future__ import annotations

from typing import Any, Mapping


def resolve_initial_cron_delivery(input: Mapping[str, Any]) -> dict[str, Any] | None:
    """Resolve default cron delivery for new jobs when callers omit explicit delivery config.

    Returns the explicit ``delivery`` if present. Otherwise, for isolated session
    targets with agentTurn/command payloads, returns ``{"mode": "announce"}``.
    """
    delivery = input.get("delivery")
    if delivery is not None:
        return delivery  # type: ignore[return-value]
    session_target = input.get("sessionTarget")
    payload = input.get("payload")
    payload_kind = payload.get("kind") if isinstance(payload, Mapping) else None
    if session_target == "isolated" and payload_kind in ("agentTurn", "command"):
        return {"mode": "announce"}
    return None
