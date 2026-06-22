"""Estimates prompt pressure and decides pre-prompt compaction routing."""

from __future__ import annotations

import json
import math
from typing import Any, TypedDict

from openclaw.agents.agent_compaction_constants import (
    MIN_PROMPT_BUDGET_RATIO,
    MIN_PROMPT_BUDGET_TOKENS,
)
from openclaw.agents.compaction_planning import SAFETY_MARGIN
from openclaw.agents.embedded_agent_runner.run.preemptive_compaction_types import (
    PreemptiveCompactionRoute,
)
from openclaw.agents.embedded_agent_runner.tool_result_reduction import (
    estimate_tool_result_reduction_potential,
)

PREEMPTIVE_OVERFLOW_ERROR_TEXT = (
    "Context overflow: prompt too large for the model (precheck)."
)

ESTIMATED_CHARS_PER_TOKEN = 4
TOOL_RESULT_CHARS_PER_TOKEN = 2
JSON_PAYLOAD_CHARS_PER_TOKEN = 3
MESSAGE_BOUNDARY_OVERHEAD_TOKENS = 12
CONTENT_BLOCK_OVERHEAD_TOKENS = 6
IMAGE_BLOCK_TOKENS = 2_000
TRUNCATION_ROUTE_BUFFER_TOKENS = 512


class LlmBoundaryTokenPressure(TypedDict, total=False):
    estimatedPromptTokens: int
    source: str
    renderedChars: int


class PreemptiveCompactionDecision(TypedDict):
    route: PreemptiveCompactionRoute
    shouldCompact: bool
    estimatedPromptTokens: int
    pressureSource: str | None
    promptBudgetBeforeReserve: int
    overflowTokens: int
    toolResultReducibleChars: int
    effectiveReserveTokens: int


class SessionContextBudgetStatus(TypedDict, total=False):
    schemaVersion: int
    source: str
    updatedAt: int
    provider: str
    model: str
    route: PreemptiveCompactionRoute
    shouldCompact: bool
    estimatedPromptTokens: int
    contextTokenBudget: int
    promptBudgetBeforeReserve: int
    reserveTokens: int
    effectiveReserveTokens: int
    remainingPromptBudgetTokens: int
    overflowTokens: int
    toolResultReducibleChars: int
    messageCount: int
    unwindowedMessageCount: int
    sessionId: str


def _estimate_string_chars(text: str) -> int:
    return len(text)


def _estimate_string_token_pressure(text: str, chars_per_token: int = ESTIMATED_CHARS_PER_TOKEN) -> int:
    return math.ceil(_estimate_string_chars(text) / chars_per_token)


def _estimate_json_payload_token_pressure(
    value: object,
    chars_per_token: int = JSON_PAYLOAD_CHARS_PER_TOKEN,
) -> int:
    try:
        serialized = json.dumps(value)
        return math.ceil(_estimate_string_chars(serialized) / chars_per_token)
    except (TypeError, ValueError):
        return 256


def _estimate_identifier_token_pressure(
    value: object,
    chars_per_token: int = JSON_PAYLOAD_CHARS_PER_TOKEN,
) -> int:
    if value is None:
        return 0
    if isinstance(value, (str, int, float, bool)):
        return _estimate_string_token_pressure(str(value), chars_per_token)
    return _estimate_json_payload_token_pressure(value, chars_per_token)


def _is_record(block: object) -> bool:
    return isinstance(block, dict)


def _estimate_content_block_token_pressure(
    block: object,
    chars_per_token: int = ESTIMATED_CHARS_PER_TOKEN,
) -> int:
    if isinstance(block, str):
        return _estimate_string_token_pressure(block, chars_per_token)
    if not _is_record(block):
        return _estimate_json_payload_token_pressure(block, chars_per_token)

    btype = block.get("type")
    if btype == "text" and isinstance(block.get("text"), str):
        return CONTENT_BLOCK_OVERHEAD_TOKENS + _estimate_string_token_pressure(
            block["text"], chars_per_token
        )
    if btype == "thinking" and isinstance(block.get("thinking"), str):
        return CONTENT_BLOCK_OVERHEAD_TOKENS + _estimate_string_token_pressure(
            block["thinking"], chars_per_token
        )
    if btype == "image":
        return IMAGE_BLOCK_TOKENS
    return CONTENT_BLOCK_OVERHEAD_TOKENS + _estimate_json_payload_token_pressure(block, chars_per_token)


def _estimate_tool_result_content_token_pressure(content: object) -> int:
    if isinstance(content, str):
        return _estimate_string_token_pressure(content, TOOL_RESULT_CHARS_PER_TOKEN)
    if isinstance(content, list):
        return sum(
            _estimate_content_block_token_pressure(b, TOOL_RESULT_CHARS_PER_TOKEN) for b in content
        )
    if content is not None:
        return _estimate_json_payload_token_pressure(content, TOOL_RESULT_CHARS_PER_TOKEN)
    return 0


def _estimate_assistant_tool_call_token_pressure(block: dict[str, Any]) -> int:
    args = block.get("arguments") or block.get("input") or block.get("args") or {}
    return (
        CONTENT_BLOCK_OVERHEAD_TOKENS
        + _estimate_identifier_token_pressure(block.get("name"), JSON_PAYLOAD_CHARS_PER_TOKEN)
        + _estimate_json_payload_token_pressure(args, JSON_PAYLOAD_CHARS_PER_TOKEN)
    )


def _estimate_content_token_pressure(content: object) -> int:
    if isinstance(content, str):
        return _estimate_string_token_pressure(content)
    if isinstance(content, list):
        return sum(_estimate_content_block_token_pressure(b) for b in content)
    if content is not None:
        return _estimate_json_payload_token_pressure(content)
    return 0


def _is_tool_result_message(message: dict[str, Any]) -> bool:
    role = message.get("role")
    mtype = message.get("type")
    return role in ("toolResult", "tool") or mtype == "toolResult"


def _estimate_message_token_pressure(message: dict[str, Any]) -> int:
    tokens = MESSAGE_BOUNDARY_OVERHEAD_TOKENS

    if _is_tool_result_message(message):
        tokens += _estimate_tool_result_content_token_pressure(message.get("content"))
        tokens += _estimate_identifier_token_pressure(
            message.get("toolName") or message.get("tool_name")
        )
        return tokens

    if message.get("role") == "assistant":
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if (
                    _is_record(block)
                    and block.get("type") in ("toolCall", "tool_use")
                ):
                    tokens += _estimate_assistant_tool_call_token_pressure(block)
                else:
                    tokens += _estimate_content_block_token_pressure(block)
        else:
            tokens += _estimate_content_token_pressure(content)

        tool_calls = message.get("toolCalls") or message.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if _is_record(tool_call):
                    tokens += _estimate_assistant_tool_call_token_pressure(tool_call)
                else:
                    tokens += _estimate_json_payload_token_pressure(tool_call)
        return tokens

    tokens += _estimate_content_token_pressure(message.get("content"))
    return tokens


def estimate_llm_boundary_token_pressure(
    *,
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
    prompt: str,
) -> int:
    history_tokens = sum(_estimate_message_token_pressure(m) for m in messages)
    system_tokens = 0
    if isinstance(system_prompt, str) and system_prompt.strip():
        system_tokens = MESSAGE_BOUNDARY_OVERHEAD_TOKENS + _estimate_string_token_pressure(
            system_prompt
        )
    prompt_tokens = MESSAGE_BOUNDARY_OVERHEAD_TOKENS + _estimate_string_token_pressure(prompt)
    return max(0, math.ceil((history_tokens + system_tokens + prompt_tokens) * SAFETY_MARGIN))


def estimate_rendered_llm_boundary_token_pressure(
    *,
    system_prompt: str | None = None,
    prompt: str,
) -> int:
    system_tokens = 0
    if isinstance(system_prompt, str) and system_prompt.strip():
        system_tokens = MESSAGE_BOUNDARY_OVERHEAD_TOKENS + _estimate_string_token_pressure(
            system_prompt
        )
    prompt_tokens = MESSAGE_BOUNDARY_OVERHEAD_TOKENS + _estimate_string_token_pressure(prompt)
    return max(0, math.ceil((system_tokens + prompt_tokens) * SAFETY_MARGIN))


def _normalize_llm_boundary_token_pressure(
    pressure: LlmBoundaryTokenPressure | None,
) -> LlmBoundaryTokenPressure | None:
    if not pressure:
        return None
    est = pressure.get("estimatedPromptTokens")
    if not isinstance(est, (int, float)) or not math.isfinite(est):
        return None
    estimated = max(0, math.ceil(float(est)))
    source = (pressure.get("source") or "").strip() or "rendered_llm_boundary"
    out: LlmBoundaryTokenPressure = {"estimatedPromptTokens": estimated, "source": source}
    rendered = pressure.get("renderedChars")
    if isinstance(rendered, (int, float)) and math.isfinite(rendered):
        out["renderedChars"] = max(0, math.ceil(float(rendered)))
    return out


def should_preemptively_compact_before_prompt(
    *,
    messages: list[dict[str, Any]],
    unwindowed_messages: list[dict[str, Any]] | None = None,
    system_prompt: str | None = None,
    prompt: str,
    context_token_budget: int,
    reserve_tokens: int,
    tool_result_max_chars: int | None = None,
    llm_boundary_token_pressure: LlmBoundaryTokenPressure | None = None,
) -> PreemptiveCompactionDecision:
    messages_for_pressure = messages
    llm_pressure = _normalize_llm_boundary_token_pressure(llm_boundary_token_pressure)
    if llm_pressure:
        estimated_prompt_tokens = llm_pressure["estimatedPromptTokens"]
        pressure_source = llm_pressure.get("source") or "rendered_llm_boundary"
    else:
        estimated_prompt_tokens = estimate_llm_boundary_token_pressure(
            messages=messages,
            system_prompt=system_prompt,
            prompt=prompt,
        )
        pressure_source = "transcript_estimate"

    if unwindowed_messages is not None and unwindowed_messages is not messages:
        unwindowed_est = estimate_llm_boundary_token_pressure(
            messages=unwindowed_messages,
            system_prompt=system_prompt,
            prompt=prompt,
        )
        if unwindowed_est > estimated_prompt_tokens:
            estimated_prompt_tokens = unwindowed_est
            messages_for_pressure = unwindowed_messages
            pressure_source = "unwindowed_transcript_estimate"

    context_budget = max(1, int(context_token_budget))
    requested_reserve = max(0, int(reserve_tokens))
    min_prompt_budget = min(
        MIN_PROMPT_BUDGET_TOKENS,
        max(1, int(context_budget * MIN_PROMPT_BUDGET_RATIO)),
    )
    effective_reserve = min(requested_reserve, max(0, context_budget - min_prompt_budget))
    prompt_budget_before_reserve = max(1, context_budget - effective_reserve)
    overflow_tokens = max(0, estimated_prompt_tokens - prompt_budget_before_reserve)

    tool_potential = estimate_tool_result_reduction_potential(
        messages=messages_for_pressure,
        context_window_tokens=context_token_budget,
        max_chars_override=tool_result_max_chars,
    )
    overflow_chars = overflow_tokens * ESTIMATED_CHARS_PER_TOKEN
    truncation_buffer_chars = TRUNCATION_ROUTE_BUFFER_TOKENS * ESTIMATED_CHARS_PER_TOKEN
    truncate_only_threshold_chars = max(
        overflow_chars + truncation_buffer_chars,
        math.ceil(overflow_chars * 1.5),
    )
    tool_result_reducible_chars = tool_potential["maxReducibleChars"]

    route: PreemptiveCompactionRoute = "fits"
    if overflow_tokens > 0:
        if tool_result_reducible_chars <= 0:
            route = "compact_only"
        elif tool_result_reducible_chars >= truncate_only_threshold_chars:
            route = "truncate_tool_results_only"
        else:
            route = "compact_then_truncate"

    return {
        "route": route,
        "shouldCompact": route in ("compact_only", "compact_then_truncate"),
        "estimatedPromptTokens": estimated_prompt_tokens,
        "pressureSource": pressure_source,
        "promptBudgetBeforeReserve": prompt_budget_before_reserve,
        "overflowTokens": overflow_tokens,
        "toolResultReducibleChars": tool_result_reducible_chars,
        "effectiveReserveTokens": effective_reserve,
    }


def format_pre_prompt_precheck_log(
    *,
    result: PreemptiveCompactionDecision,
    session_key: str | None = None,
    session_id: str | None = None,
    provider: str,
    model_id: str,
    message_count: int,
    unwindowed_message_count: int | None = None,
    context_token_budget: int,
    reserve_tokens: int,
    session_file: str | None = None,
) -> str:
    sk = session_key or session_id or "unknown"
    uw = unwindowed_message_count if unwindowed_message_count is not None else message_count
    return (
        f"[context-overflow-precheck] pre-prompt check "
        f"sessionKey={sk} "
        f"provider={provider}/{model_id} "
        f"route={result['route']} "
        f"estimatedPromptTokens={result['estimatedPromptTokens']} "
        f"pressureSource={result.get('pressureSource') or 'unknown'} "
        f"promptBudgetBeforeReserve={result['promptBudgetBeforeReserve']} "
        f"overflowTokens={result['overflowTokens']} "
        f"toolResultReducibleChars={result['toolResultReducibleChars']} "
        f"reserveTokens={reserve_tokens} "
        f"effectiveReserveTokens={result['effectiveReserveTokens']} "
        f"contextTokenBudget={context_token_budget} "
        f"messages={message_count} "
        f"unwindowedMessages={uw} "
        f"sessionFile={session_file}"
    )


def build_pre_prompt_context_budget_status(
    *,
    result: PreemptiveCompactionDecision,
    provider: str,
    model_id: str,
    message_count: int,
    unwindowed_message_count: int | None = None,
    context_token_budget: int,
    reserve_tokens: int,
    session_id: str | None = None,
    now: int | None = None,
) -> SessionContextBudgetStatus:
    import time

    remaining = max(0, result["promptBudgetBeforeReserve"] - result["estimatedPromptTokens"])
    uw = unwindowed_message_count if unwindowed_message_count is not None else message_count
    status: SessionContextBudgetStatus = {
        "schemaVersion": 1,
        "source": "pre-prompt-estimate",
        "updatedAt": now if now is not None else int(time.time() * 1000),
        "provider": provider,
        "model": model_id,
        "route": result["route"],
        "shouldCompact": result["shouldCompact"],
        "estimatedPromptTokens": result["estimatedPromptTokens"],
        "contextTokenBudget": max(1, int(context_token_budget)),
        "promptBudgetBeforeReserve": result["promptBudgetBeforeReserve"],
        "reserveTokens": max(0, int(reserve_tokens)),
        "effectiveReserveTokens": result["effectiveReserveTokens"],
        "remainingPromptBudgetTokens": remaining,
        "overflowTokens": result["overflowTokens"],
        "toolResultReducibleChars": result["toolResultReducibleChars"],
        "messageCount": max(0, int(message_count)),
        "unwindowedMessageCount": max(0, int(uw)),
    }
    if session_id:
        status["sessionId"] = session_id
    return status