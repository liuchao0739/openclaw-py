"""Reasoning effort utilities map provider thinking controls to runtime levels.

Mirrors src/llm/providers/stream-wrappers/reasoning-effort-utils.ts.
"""

from __future__ import annotations

from typing import Literal

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
ThinkLevel = Literal["off", "adaptive", "max", "minimal", "low", "medium", "high"]


def map_thinking_level_to_reasoning_effort(thinking_level: str) -> str:
    """Map OpenClaw thinking levels onto provider reasoning-effort labels."""
    if thinking_level == "off":
        return "none"
    if thinking_level == "adaptive":
        return "medium"
    if thinking_level == "max":
        return "xhigh"
    return thinking_level
