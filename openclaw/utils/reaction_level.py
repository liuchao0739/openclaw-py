from __future__ import annotations

from typing import Any, Literal, TypedDict

ReactionLevel = Literal["off", "ack", "minimal", "extensive"]


class ResolvedReactionLevel(TypedDict):
    level: ReactionLevel
    ackEnabled: bool
    agentReactionsEnabled: bool
    agentReactionGuidance: Literal["minimal", "extensive"] | None


_LEVELS = {"off", "ack", "minimal", "extensive"}


def _parse_level(value: Any) -> dict:
    if value is None:
        return {"kind": "missing"}
    if not isinstance(value, str):
        return {"kind": "invalid"}
    trimmed = value.strip()
    if not trimmed:
        return {"kind": "missing"}
    if trimmed in _LEVELS:
        return {"kind": "ok", "value": trimmed}
    return {"kind": "invalid"}


def resolve_reaction_level(params: dict) -> ResolvedReactionLevel:
    parsed = _parse_level(params["value"])
    if parsed["kind"] == "ok":
        effective = parsed["value"]
    elif parsed["kind"] == "missing":
        effective = params["defaultLevel"]
    else:
        effective = params["invalidFallback"]

    if effective == "off":
        return {"level": "off", "ackEnabled": False, "agentReactionsEnabled": False, "agentReactionGuidance": None}
    if effective == "ack":
        return {"level": "ack", "ackEnabled": True, "agentReactionsEnabled": False, "agentReactionGuidance": None}
    if effective == "minimal":
        return {
            "level": "minimal",
            "ackEnabled": False,
            "agentReactionsEnabled": True,
            "agentReactionGuidance": "minimal",
        }
    if effective == "extensive":
        return {
            "level": "extensive",
            "ackEnabled": False,
            "agentReactionsEnabled": True,
            "agentReactionGuidance": "extensive",
        }
    return {
        "level": "minimal",
        "ackEnabled": False,
        "agentReactionsEnabled": True,
        "agentReactionGuidance": "minimal",
    }
