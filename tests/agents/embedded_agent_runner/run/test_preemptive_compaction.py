"""Tests for preemptive compaction (P2-0012)."""

from openclaw.agents.embedded_agent_runner.run.preemptive_compaction import (
    PREEMPTIVE_OVERFLOW_ERROR_TEXT,
    build_pre_prompt_context_budget_status,
    estimate_llm_boundary_token_pressure,
    estimate_rendered_llm_boundary_token_pressure,
    format_pre_prompt_precheck_log,
    should_preemptively_compact_before_prompt,
)
from openclaw.agents.embedded_agent_runner.tool_result_reduction import (
    estimate_tool_result_reduction_potential,
)

_timestamp = 1


def _make_assistant_history(text: str) -> dict:
    global _timestamp
    msg = {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "timestamp": _timestamp,
    }
    _timestamp += 1
    return msg


def _make_tool_result_message(*texts: str) -> dict:
    global _timestamp
    msg = {
        "role": "toolResult",
        "toolCallId": f"call_{_timestamp}",
        "toolName": "read",
        "content": [{"type": "text", "text": t} for t in texts],
        "isError": False,
        "timestamp": _timestamp,
    }
    _timestamp += 1
    return msg


def _make_json_tool_result_message(payload: object) -> dict:
    global _timestamp
    msg = {
        "role": "toolResult",
        "toolCallId": f"call_{_timestamp}",
        "toolName": "json_tool",
        "content": [{"type": "json", "payload": payload}],
        "isError": False,
        "timestamp": _timestamp,
    }
    _timestamp += 1
    return msg


def _make_assistant_tool_call(args: object) -> dict:
    global _timestamp
    msg = {
        "role": "assistant",
        "content": [
            {
                "type": "toolCall",
                "id": f"call_{_timestamp}",
                "name": "bulk_lookup",
                "arguments": args,
            }
        ],
        "timestamp": _timestamp,
    }
    _timestamp += 1
    return msg


VERBOSE_HISTORY = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu " * 40
)
VERBOSE_SYSTEM = (
    "system guidance with multiple distinct words to avoid tokenizer overcompression " * 25
)
VERBOSE_PROMPT = (
    "user request with distinct content asking for a detailed answer and more context " * 25
)


def test_overflow_error_text():
    assert "Context overflow:" in PREEMPTIVE_OVERFLOW_ERROR_TEXT
    assert "(precheck)" in PREEMPTIVE_OVERFLOW_ERROR_TEXT


def test_estimate_grows_with_content():
    smaller = estimate_llm_boundary_token_pressure(
        messages=[_make_assistant_history(VERBOSE_HISTORY)],
        system_prompt="sys",
        prompt="hello",
    )
    larger = estimate_llm_boundary_token_pressure(
        messages=[_make_assistant_history(VERBOSE_HISTORY)],
        system_prompt=VERBOSE_SYSTEM,
        prompt=VERBOSE_PROMPT,
    )
    assert larger > smaller


def test_preemptive_compact_when_over_budget():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history(VERBOSE_HISTORY)],
        system_prompt=VERBOSE_SYSTEM,
        prompt=VERBOSE_PROMPT,
        context_token_budget=500,
        reserve_tokens=50,
    )
    assert result["shouldCompact"] is True
    assert result["route"] == "compact_only"
    assert result["estimatedPromptTokens"] > result["promptBudgetBeforeReserve"]


def test_fits_when_under_budget():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("short history")],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=10_000,
        reserve_tokens=1_000,
    )
    assert result["shouldCompact"] is False
    assert result["route"] == "fits"
    assert result["estimatedPromptTokens"] < result["promptBudgetBeforeReserve"]


def test_format_precheck_log():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("short history")],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=10_000,
        reserve_tokens=1_000,
    )
    line = format_pre_prompt_precheck_log(
        result=result,
        session_key="discord:channel:thread",
        session_id="session-1",
        provider="anthropic",
        model_id="claude-opus-4-6",
        message_count=1,
        unwindowed_message_count=3,
        context_token_budget=10_000,
        reserve_tokens=1_000,
        session_file="sessions/session-1.json",
    )
    assert "[context-overflow-precheck] pre-prompt check" in line
    assert "route=fits" in line
    assert "overflowTokens=0" in line


def test_build_context_budget_status():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("short history")],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=10_000,
        reserve_tokens=1_000,
    )
    status = build_pre_prompt_context_budget_status(
        result=result,
        provider="anthropic",
        model_id="claude-opus-4-6",
        message_count=1,
        unwindowed_message_count=3,
        context_token_budget=10_000,
        reserve_tokens=1_000,
        session_id="session-1",
        now=123,
    )
    assert status["schemaVersion"] == 1
    assert status["source"] == "pre-prompt-estimate"
    assert status["updatedAt"] == 123
    assert status["route"] == "fits"
    assert status["remainingPromptBudgetTokens"] == (
        result["promptBudgetBeforeReserve"] - result["estimatedPromptTokens"]
    )


def test_unwindowed_messages_higher_pressure():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("small assembled window")],
        unwindowed_messages=[_make_assistant_history(VERBOSE_HISTORY * 4)],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=500,
        reserve_tokens=50,
    )
    assert result["shouldCompact"] is True
    assert result["route"] == "compact_only"


def test_rendered_llm_boundary_pressure():
    rendered_prompt = "x" * 60_000
    estimated = estimate_rendered_llm_boundary_token_pressure(
        system_prompt="sys",
        prompt=rendered_prompt,
    )
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("the transcript view is intentionally small")],
        system_prompt="sys",
        prompt="small prompt before runtime projection",
        context_token_budget=16_000,
        reserve_tokens=4_000,
        llm_boundary_token_pressure={
            "estimatedPromptTokens": estimated,
            "source": "test_rendered_payload",
            "renderedChars": len(rendered_prompt),
        },
    )
    assert result["pressureSource"] == "test_rendered_payload"
    assert result["estimatedPromptTokens"] == estimated
    assert result["route"] == "compact_only"


def test_json_tool_result_at_boundary():
    object_payload = {
        "rows": [
            {"path": f"/tmp/generated-{i}.txt", "body": "x" * 1_500}
            for i in range(120)
        ],
    }
    messages = [_make_json_tool_result_message(object_payload)]
    estimated = estimate_llm_boundary_token_pressure(
        messages=messages,
        system_prompt="sys",
        prompt="continue",
    )
    assert estimated > 80_000


def test_assistant_tool_call_arguments_counted():
    messages = [
        _make_assistant_tool_call(
            {
                "queryPlan": "find relevant files",
                "candidates": [
                    {"path": f"/repo/file-{index}.ts", "content": "z" * 1_000}
                    for index in range(100)
                ],
            }
        )
    ]
    estimated = estimate_llm_boundary_token_pressure(
        messages=messages,
        system_prompt="sys",
        prompt="continue",
    )
    assert estimated > 30_000


def test_effective_reserve_capped_for_small_context():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("short history")],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=16_000,
        reserve_tokens=20_000,
    )
    assert result["effectiveReserveTokens"] == 8_000
    assert result["promptBudgetBeforeReserve"] == 8_000
    assert result["route"] == "fits"


def test_keeps_reserve_when_enough_prompt_budget():
    result = should_preemptively_compact_before_prompt(
        messages=[_make_assistant_history("short history")],
        system_prompt="sys",
        prompt="hello",
        context_token_budget=32_000,
        reserve_tokens=20_000,
    )
    assert result["effectiveReserveTokens"] == 20_000
    assert result["promptBudgetBeforeReserve"] == 12_000