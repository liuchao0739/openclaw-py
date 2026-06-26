"""Tests for agents/runtime facade and proxy."""

from openclaw.agents.runtime import (
    Agent,
    OpenClawAgentCoreRuntime,
    openclaw_agent_core_runtime,
    build_proxy_request_options,
    sanitize_proxy_model,
    process_proxy_event,
    ProxyStreamOptions,
)


class TestOpenClawAgentCoreRuntime:
    def test_not_configured_raises(self):
        rt = OpenClawAgentCoreRuntime()
        import asyncio
        try:
            asyncio.run(rt.complete_simple())
            assert False
        except RuntimeError:
            pass

    def test_stream_not_configured_raises(self):
        rt = OpenClawAgentCoreRuntime()
        try:
            rt.stream_simple()
            assert False
        except RuntimeError:
            pass

    def test_set_and_call_complete(self):
        import asyncio

        async def fake_complete(msg: str) -> str:
            return f"reply:{msg}"

        rt = OpenClawAgentCoreRuntime()
        rt.set_complete_simple(fake_complete)
        result = asyncio.run(rt.complete_simple("hello"))
        assert result == "reply:hello"

    def test_set_and_call_stream(self):
        def fake_stream(msg: str) -> str:
            return f"stream:{msg}"

        rt = OpenClawAgentCoreRuntime()
        rt.set_stream_simple(fake_stream)
        assert rt.stream_simple("hi") == "stream:hi"

    def test_singleton(self):
        assert openclaw_agent_core_runtime is not None
        assert isinstance(openclaw_agent_core_runtime, OpenClawAgentCoreRuntime)


class TestAgent:
    def test_defaults(self):
        agent = Agent()
        assert agent.system is None
        assert agent.tools == []
        assert agent.max_turns == 0
        assert agent.runtime is openclaw_agent_core_runtime

    def test_options(self):
        agent = Agent({"maxTurns": 10})
        assert agent.options["maxTurns"] == 10

    def test_system_setter(self):
        agent = Agent()
        agent.system = "you are helpful"
        assert agent.system == "you are helpful"

    def test_add_tool(self):
        agent = Agent()
        agent.add_tool({"name": "search"})
        assert len(agent.tools) == 1

    def test_max_turns(self):
        agent = Agent()
        agent.max_turns = 5
        assert agent.max_turns == 5


class TestProxyHelpers:
    def test_build_request_options(self):
        opts = {
            "temperature": 0.7,
            "maxTokens": 1000,
            "sessionId": "s1",
            "extraKey": "ignored",
        }
        result = build_proxy_request_options(opts)
        assert result["temperature"] == 0.7
        assert result["maxTokens"] == 1000
        assert result["sessionId"] == "s1"
        assert "extraKey" not in result

    def test_build_empty(self):
        assert build_proxy_request_options({}) == {}

    def test_sanitize_model(self):
        model = {"name": "gpt-4", "headers": {"auth": "secret"}}
        safe = sanitize_proxy_model(model)
        assert "headers" not in safe
        assert safe["name"] == "gpt-4"

    def test_sanitize_no_headers(self):
        model = {"name": "gpt-4"}
        safe = sanitize_proxy_model(model)
        assert safe == {"name": "gpt-4"}

    def test_process_start_event(self):
        partial: dict = {}
        result = process_proxy_event({"type": "start"}, partial)
        assert result["type"] == "start"

    def test_process_text_events(self):
        partial: dict = {}
        process_proxy_event({"type": "start"}, partial)
        process_proxy_event({"type": "text_start", "contentIndex": 0}, partial)
        result = process_proxy_event({"type": "text_delta", "contentIndex": 0, "delta": "hello"}, partial)
        assert result["type"] == "text_delta"
        assert partial["content"][0]["text"] == "hello"

    def test_process_done_event(self):
        partial: dict = {}
        result = process_proxy_event({"type": "done", "reason": "stop", "usage": {"tokens": 10}}, partial)
        assert result["type"] == "done"
        assert partial["stopReason"] == "stop"
        assert partial["usage"]["tokens"] == 10

    def test_process_error_event(self):
        partial: dict = {}
        result = process_proxy_event({"type": "error", "reason": "timeout", "errorMessage": "timed out"}, partial)
        assert result["type"] == "error"
        assert partial["stopReason"] == "timeout"
        assert partial["errorMessage"] == "timed out"

    def test_process_unknown_event(self):
        partial: dict = {}
        result = process_proxy_event({"type": "unknown"}, partial)
        assert result is None
