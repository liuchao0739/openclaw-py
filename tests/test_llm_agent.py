"""LLM and agent loop tests."""

from __future__ import annotations

import pytest

from openclaw.agents.loop import run_agent_loop
from openclaw.agents.terminal_outcome import (
    AgentRunTerminalReason,
    AgentRunWaitStatus,
    normalize_agent_run_terminal_outcome,
)
from openclaw.llm.core import Model, ModelRef, Tool, UserMessage
from openclaw.llm.runtime import build_openai_chat_completion_request


def test_model_ref_key() -> None:
    assert ModelRef(provider="openai", model="gpt-4").as_key() == "openai/gpt-4"


def test_build_openai_chat_completion_request() -> None:
    model = Model(
        id="gpt-4",
        name="GPT-4",
        api="openai-completions",
        provider="openai",
        baseUrl="https://api.openai.com/v1",
    )
    body = build_openai_chat_completion_request(
        model,
        [UserMessage(content="hello", timestamp=1)],
        tools=[Tool(name="echo", description="echo", parameters={"type": "object"})],
    )
    assert body["model"] == "gpt-4"
    assert body["messages"][0]["content"] == "hello"
    assert body["tools"][0]["function"]["name"] == "echo"


def test_terminal_outcome_hard_timeout() -> None:
    outcome = normalize_agent_run_terminal_outcome(
        {"status": "timeout", "timeoutPhase": "provider"}
    )
    assert outcome.reason == AgentRunTerminalReason.HARD_TIMEOUT
    assert outcome.status == AgentRunWaitStatus.TIMEOUT


@pytest.mark.asyncio
async def test_agent_loop_with_tool() -> None:
    model = Model(
        id="mock",
        name="mock",
        api="openai-completions",
        provider="mock",
        baseUrl="http://localhost",
    )

    async def echo_handler(_name: str, args: dict) -> str:
        return f"tool:{args['text']}"

    transcript = await run_agent_loop(
        model=model,
        messages=[UserMessage(content="ping", timestamp=1)],
        tools=[Tool(name="echo", description="echo")],
        tool_handlers={"echo": echo_handler},
        max_rounds=2,
    )
    roles = [getattr(m, "role", None) for m in transcript]
    assert roles.count("assistant") >= 1
    assert "toolResult" in roles
