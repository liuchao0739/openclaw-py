"""Native Anthropic replay hooks for Anthropic Vertex provider registration."""

from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty


def _should_preserve_thinking_blocks(model_id: str | None) -> bool:
    model_id_normalized = normalize_lowercase_string_or_empty(model_id)
    if "claude" not in model_id_normalized:
        return False
    if (
        "fable-5" in model_id_normalized
        or "opus-4" in model_id_normalized
        or "sonnet-4" in model_id_normalized
        or "haiku-4" in model_id_normalized
    ):
        return True
    return bool(
        re.search(r"claude-[5-9]", model_id_normalized)
        or re.search(r"claude-\d{2,}", model_id_normalized)
    )


def _build_strict_anthropic_replay_policy(
    *,
    drop_thinking_blocks: bool = False,
    sanitize_tool_call_ids: bool = True,
    preserve_native_anthropic_tool_use_ids: bool = False,
) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "sanitizeMode": "full",
        "preserveSignatures": True,
        "repairToolUseResultPairing": True,
        "validateAnthropicTurns": True,
        "allowSyntheticToolResults": True,
    }
    if sanitize_tool_call_ids:
        policy["sanitizeToolCallIds"] = True
        policy["toolCallIdMode"] = "strict"
        if preserve_native_anthropic_tool_use_ids:
            policy["preserveNativeAnthropicToolUseIds"] = True
    if drop_thinking_blocks:
        policy["dropThinkingBlocks"] = True
    return policy


def build_native_anthropic_replay_policy_for_model(model_id: str | None = None) -> dict[str, Any]:
    is_claude = "claude" in normalize_lowercase_string_or_empty(model_id)
    return _build_strict_anthropic_replay_policy(
        drop_thinking_blocks=is_claude and not _should_preserve_thinking_blocks(model_id),
        sanitize_tool_call_ids=True,
        preserve_native_anthropic_tool_use_ids=True,
    )


NATIVE_ANTHROPIC_REPLAY_HOOKS = {
    "buildReplayPolicy": lambda ctx: build_native_anthropic_replay_policy_for_model(
        ctx.get("modelId")
    ),
}
