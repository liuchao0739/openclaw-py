"""Tests for agents root — defaults, types, promise, idempotency, tool support, api families, content blocks."""

from __future__ import annotations

import pytest

from openclaw.agents.announce_idempotency import (
    clear_announced,
    has_announced,
    mark_announced,
)
from openclaw.agents.bash_tools import (
    BASH_TOOL_NAME,
    DEFAULT_BASH_TIMEOUT_MS,
    SAFE_COMMANDS,
)
from openclaw.agents.content_blocks import TextContentBlock
from openclaw.agents.defaults import DEFAULT_CONTEXT_TOKENS, DEFAULT_MODEL, DEFAULT_PROVIDER
from openclaw.agents.embedded_agent_subscribe_promise import is_awaitable, is_promise_like
from openclaw.agents.embedded_agent_subscribe_shared_types import ToolResultFormat
from openclaw.agents.model_tool_support import (
    supports_function_calling,
    supports_parallel_tool_calls,
    supports_streaming,
    supports_vision,
)
from openclaw.agents.provider_api_families import get_provider_api_family, register_provider_api_family
from openclaw.agents.subagent_registry_memory import (
    clear_subagent_runs,
    get_subagent_run,
    remove_subagent_run,
    set_subagent_run,
)
from openclaw.agents.subagent_spawn_types import SUBAGENT_SPAWN_MODES
from openclaw.agents.system_prompt_types import PromptMode
from openclaw.agents.tool_fs_policy_types import ToolFsPolicy


class TestDefaults:
    def test_constants(self):
        assert DEFAULT_PROVIDER == "openai"
        assert DEFAULT_MODEL == "gpt-5.5"
        assert DEFAULT_CONTEXT_TOKENS == 200_000


class TestAnnounceIdempotency:
    def setup_method(self):
        clear_announced()

    def test_mark_and_check(self):
        assert not has_announced("s1", "t1")
        assert mark_announced("s1", "t1") is True
        assert has_announced("s1", "t1")
        assert mark_announced("s1", "t1") is False  # duplicate

    def test_different_targets(self):
        mark_announced("s1", "t1")
        assert not has_announced("s1", "t2")
        assert mark_announced("s1", "t2") is True

    def test_with_channel(self):
        mark_announced("s1", "t1", channel="telegram")
        assert not has_announced("s1", "t1", channel="discord")
        assert has_announced("s1", "t1", channel="telegram")

    def test_clear(self):
        mark_announced("s1", "t1")
        clear_announced()
        assert not has_announced("s1", "t1")


class TestSubagentRegistryMemory:
    def setup_method(self):
        clear_subagent_runs()

    def test_set_and_get(self):
        set_subagent_run("r1", {"status": "running"})
        assert get_subagent_run("r1") == {"status": "running"}

    def test_get_missing(self):
        assert get_subagent_run("nonexistent") is None

    def test_remove(self):
        set_subagent_run("r1", {"status": "done"})
        remove_subagent_run("r1")
        assert get_subagent_run("r1") is None

    def test_clear(self):
        set_subagent_run("r1", {})
        set_subagent_run("r2", {})
        clear_subagent_runs()
        assert get_subagent_run("r1") is None
        assert get_subagent_run("r2") is None


class TestModelToolSupport:
    def test_supports_function_calling_default(self):
        assert supports_function_calling(None) is True

    def test_supports_function_calling_disabled(self):
        assert supports_function_calling({"toolCallCapable": False}) is False

    def test_supports_parallel_default(self):
        assert supports_parallel_tool_calls(None) is True

    def test_supports_vision(self):
        assert supports_vision({"input": ["text", "image"]}) is True
        assert supports_vision({"input": ["text"]}) is False
        assert supports_vision(None) is False

    def test_supports_streaming(self):
        assert supports_streaming(None) is True
        assert supports_streaming({"streamingCapable": False}) is False


class TestProviderApiFamilies:
    def test_known_providers(self):
        assert get_provider_api_family("openai") == "openai-responses"
        assert get_provider_api_family("anthropic") == "anthropic-messages"
        assert get_provider_api_family("google") == "google-gemini"

    def test_unknown_provider(self):
        assert get_provider_api_family("unknown") == "generic"
        assert get_provider_api_family(None) == "generic"

    def test_register(self):
        register_provider_api_family("custom", "openai-chat")
        assert get_provider_api_family("custom") == "openai-chat"


class TestPromiseLike:
    def test_awaitable_coroutine(self):
        import asyncio

        async def coro():
            pass

        assert is_awaitable(coro()) is True

    def test_awaitable_non_coroutine(self):
        assert is_awaitable(42) is False
        assert is_awaitable("hello") is False

    def test_promise_like_with_then(self):
        class FakePromise:
            def then(self, callback):
                pass

        assert is_promise_like(FakePromise()) is True

    def test_promise_like_without_then(self):
        assert is_promise_like(42) is False
        assert is_promise_like("hello") is False


class TestBashTools:
    def test_constants(self):
        assert BASH_TOOL_NAME == "bash"
        assert DEFAULT_BASH_TIMEOUT_MS == 120_000
        assert "ls" in SAFE_COMMANDS
        assert "git status" in SAFE_COMMANDS


class TestSubagentSpawnTypes:
    def test_modes(self):
        assert "run" in SUBAGENT_SPAWN_MODES
        assert "session" in SUBAGENT_SPAWN_MODES
