"""Tests context-pruning settings, runtime registry, and message pruning."""

from __future__ import annotations

import time

import pytest

from openclaw.agents.agent_hooks.context_pruning import (
    DEFAULT_CONTEXT_PRUNING_SETTINGS,
    compute_effective_settings,
    prune_context_messages,
    register_context_pruning_extension,
)
from openclaw.agents.agent_hooks.context_pruning.runtime import (
    ContextPruningRuntimeValue,
    get_context_pruning_runtime,
    set_context_pruning_runtime,
)
from openclaw.agents.agent_hooks.context_pruning.settings import EffectiveContextPruningSettings
from openclaw.agents.agent_hooks.context_pruning.tools import make_tool_prunable_predicate
from openclaw.agents.sessions import ContextEvent, ExtensionContext, SimpleExtensionAPI
from openclaw.llm.core import Model, TextContent, ToolResultMessage, Usage


def _tool_text(msg: ToolResultMessage) -> str:
    for block in msg.content:
        if isinstance(block, TextContent):
            return block.text
    return ""


def make_tool_result(tool_call_id: str, tool_name: str, text: str) -> ToolResultMessage:
    return ToolResultMessage(
        toolCallId=tool_call_id,
        toolName=tool_name,
        content=[TextContent(text=text)],
        isError=False,
        timestamp=int(time.time() * 1000),
    )


def make_assistant(text: str) -> dict:
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "api": "openai-responses",
        "provider": "openai",
        "model": "fake",
        "usage": Usage().model_dump(by_alias=True),
        "stopReason": "stop",
        "timestamp": int(time.time() * 1000),
    }


def make_user(text: str) -> dict:
    return {"role": "user", "content": text, "timestamp": int(time.time() * 1000)}


def make_aggressive_settings(**overrides: object) -> EffectiveContextPruningSettings:
    base = DEFAULT_CONTEXT_PRUNING_SETTINGS
    s = EffectiveContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=base.ttl_ms,
        keep_last_assistants=0,
        soft_trim_ratio=0.0,
        hard_clear_ratio=0.0,
        min_prunable_tool_chars=0,
        tools=base.tools,
        soft_trim=base.soft_trim.__class__(max_chars=10, head_chars=3, tail_chars=3),
        hard_clear=base.hard_clear.__class__(enabled=True, placeholder="[cleared]"),
    )
    for key, val in overrides.items():
        if hasattr(s, key):
            setattr(s, key, val)
    return s


CONTEXT_WINDOW_1000 = ExtensionContext(
    model=Model(
        id="m",
        name="m",
        api="openai-responses",
        provider="openai",
        baseUrl="http://x",
        contextWindow=1000,
    )
)


def prune_aggressive(messages: list, **extra: object) -> list:
    return prune_context_messages(
        messages=messages,
        settings=make_aggressive_settings(),
        ctx=CONTEXT_WINDOW_1000,
        **extra,
    )


def find_tool(messages: list, tool_call_id: str) -> ToolResultMessage:
    for m in messages:
        if isinstance(m, ToolResultMessage) and m.tool_call_id == tool_call_id:
            return m
        if isinstance(m, dict) and m.get("role") == "toolResult" and m.get("toolCallId") == tool_call_id:
            return ToolResultMessage.model_validate(m)
    raise AssertionError(f"missing toolResult: {tool_call_id}")


def create_context_handler():
    api = SimpleExtensionAPI()
    register_context_pruning_extension(api)
    handlers = api._handlers.get("context")
    assert handlers
    return handlers[0]


def test_mode_off_disables_pruning():
    assert compute_effective_settings({"mode": "off"}) is None
    assert compute_effective_settings({}) is None
    assert compute_effective_settings({"mode": "cache-ttl"}) is not None


def test_does_not_touch_tool_results_after_last_n_assistants():
    messages = [
        make_user("u1"),
        make_assistant("a1"),
        make_tool_result("t1", "exec", "x" * 20_000),
        make_user("u2"),
        make_assistant("a2"),
        make_tool_result("t2", "exec", "y" * 20_000),
        make_user("u3"),
        make_assistant("a3"),
        make_tool_result("t3", "exec", "z" * 20_000),
        make_user("u4"),
        make_assistant("a4"),
        make_tool_result("t4", "exec", "w" * 20_000),
    ]
    settings = make_aggressive_settings(keep_last_assistants=3)
    next_msgs = prune_context_messages(
        messages=messages, settings=settings, ctx=CONTEXT_WINDOW_1000
    )
    assert "y" * 20_000 in _tool_text(find_tool(next_msgs, "t2"))
    assert "z" * 20_000 in _tool_text(find_tool(next_msgs, "t3"))
    assert "w" * 20_000 in _tool_text(find_tool(next_msgs, "t4"))
    assert _tool_text(find_tool(next_msgs, "t1")) == "[cleared]"


def test_never_prunes_before_first_user():
    messages = [
        make_assistant("bootstrap"),
        make_tool_result("t0", "read", "x" * 20_000),
        make_assistant("greeting"),
        make_user("u1"),
        make_tool_result("t1", "exec", "y" * 20_000),
    ]
    next_msgs = prune_aggressive(
        messages,
        is_tool_prunable=lambda _: True,
        context_window_tokens_override=1000,
    )
    assert _tool_text(find_tool(next_msgs, "t0")) == "x" * 20_000
    assert _tool_text(find_tool(next_msgs, "t1")) == "[cleared]"


def test_hard_clear_before_cutoff():
    messages = [
        make_user("u1"),
        make_assistant("a1"),
        make_tool_result("t1", "exec", "x" * 20_000),
        make_tool_result("t2", "exec", "y" * 20_000),
        make_user("u2"),
        make_assistant("a2"),
        make_tool_result("t3", "exec", "z" * 20_000),
    ]
    settings = make_aggressive_settings(
        keep_last_assistants=1,
        soft_trim_ratio=10.0,
    )
    next_msgs = prune_context_messages(
        messages=messages, settings=settings, ctx=CONTEXT_WINDOW_1000
    )
    assert _tool_text(find_tool(next_msgs, "t1")) == "[cleared]"
    assert _tool_text(find_tool(next_msgs, "t2")) == "[cleared]"
    assert "z" * 20_000 in _tool_text(find_tool(next_msgs, "t3"))


def test_cjk_extension_b_triggers_prune():
    extension_b = "\U00020000" * 50
    messages = [
        make_user(extension_b),
        make_tool_result("t1", "exec", "keep me"),
    ]
    settings = make_aggressive_settings(
        keep_last_assistants=0,
        soft_trim_ratio=1.0,
        hard_clear_ratio=1.0,
    )
    next_msgs = prune_context_messages(
        messages=messages,
        settings=settings,
        ctx=CONTEXT_WINDOW_1000,
        context_window_tokens_override=40,
        is_tool_prunable=lambda _: True,
    )
    assert _tool_text(find_tool(next_msgs, "t1")) == "[cleared]"


def test_context_window_override_without_model():
    messages = [
        make_user("u1"),
        make_assistant("a1"),
        make_tool_result("t1", "exec", "x" * 20_000),
        make_assistant("a2"),
    ]
    next_msgs = prune_context_messages(
        messages=messages,
        settings=make_aggressive_settings(),
        ctx=ExtensionContext(model=None),
        context_window_tokens_override=1000,
    )
    assert _tool_text(find_tool(next_msgs, "t1")) == "[cleared]"


def test_registry_drives_extension_handler():
    session_manager = object()
    set_context_pruning_runtime(
        session_manager,
        ContextPruningRuntimeValue(
            settings=make_aggressive_settings(),
            context_window_tokens=1000,
            is_tool_prunable=lambda _: True,
            drop_thinking_blocks=False,
            last_cache_touch_at=int(time.time() * 1000)
            - DEFAULT_CONTEXT_PRUNING_SETTINGS.ttl_ms
            - 1000,
        ),
    )
    messages = [
        make_user("u1"),
        make_assistant("a1"),
        make_tool_result("t1", "exec", "x" * 20_000),
        make_assistant("a2"),
    ]
    handler = create_context_handler()
    result = handler(
        ContextEvent(messages=messages),
        ExtensionContext(model=None, session_manager=session_manager),
    )
    assert result is not None
    assert _tool_text(find_tool(result["messages"], "t1")) == "[cleared]"


def test_tool_deny_glob():
    pred = make_tool_prunable_predicate(
        type(DEFAULT_CONTEXT_PRUNING_SETTINGS.tools)(deny=["read*"])
    )
    assert pred("read_file") is False
    assert pred("exec") is True