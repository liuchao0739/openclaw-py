from __future__ import annotations

from typing import Literal

from openclaw.llm.core import Model
from openclaw_packages.llm_core.model_contracts.anthropic import resolve_claude_fable5_model_identity

from .agent_types import ThinkingLevel

ENABLED_THINKING_LEVELS = frozenset(
    ["minimal", "low", "medium", "high", "xhigh", "max"]
)


def is_enabled_thinking_level(value: str) -> bool:
    return value in ENABLED_THINKING_LEVELS


def resolve_agent_reasoning_option(
    model: Model,
    thinking_level: ThinkingLevel,
) -> str | None:
    if thinking_level != "off":
        return thinking_level
    off_fallback = None
    if getattr(model, "thinkingLevelMap", None):
        off_fallback = model.thinkingLevelMap.get("off")
    if off_fallback is None and (
        model.api == "anthropic-messages"
        or model.api == "bedrock-converse-stream"
    ):
        if resolve_claude_fable5_model_identity(model) is not None:
            off_fallback = "low"
    return off_fallback if is_enabled_thinking_level(off_fallback or "") else None
