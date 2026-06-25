"""Tests for agents/sessions/extensions — types, loader, runner."""

from __future__ import annotations

import pytest

from openclaw.agents.sessions.extensions import (
    ExtensionRunner,
    create_extension_runtime,
    define_tool,
    is_bash_tool_result,
    is_edit_tool_result,
    is_read_tool_result,
    is_tool_call_event_type,
    load_extension_from_factory,
    normalize_input_event_result,
    wrap_registered_tool,
    wrap_registered_tools,
)


class TestTypeGuards:
    def test_is_bash_tool_result(self):
        assert is_bash_tool_result({"toolName": "bash"})
        assert not is_bash_tool_result({"toolName": "read"})

    def test_is_read_tool_result(self):
        assert is_read_tool_result({"toolName": "read"})
        assert not is_read_tool_result({"toolName": "bash"})

    def test_is_edit_tool_result(self):
        assert is_edit_tool_result({"toolName": "edit"})

    def test_is_tool_call_event_type(self):
        assert is_tool_call_event_type("bash", {"toolName": "bash"})
        assert not is_tool_call_event_type("bash", {"toolName": "read"})
        assert is_tool_call_event_type("my_custom", {"toolName": "my_custom"})


class TestNormalizeInputResult:
    def test_none_returns_continue(self):
        assert normalize_input_event_result(None, "hello", None) == {"action": "continue"}

    def test_handled(self):
        result = normalize_input_event_result({"action": "handled"}, "hello", None)
        assert result == {"action": "handled"}

    def test_transform(self):
        result = normalize_input_event_result(
            {"action": "transform", "text": "modified"}, "hello", None
        )
        assert result["action"] == "transform"
        assert result["text"] == "modified"

    def test_transform_preserves_images(self):
        result = normalize_input_event_result(
            {"action": "transform", "text": "modified", "images": ["img1"]},
            "hello",
            None,
        )
        assert result["images"] == ["img1"]


class TestDefineTool:
    def test_returns_tool_unchanged(self):
        tool = {"name": "my_tool", "label": "My Tool", "description": "test"}
        result = define_tool(tool)
        assert result is tool


class TestCreateExtensionRuntime:
    def test_throws_on_uninitialized_action(self):
        runtime = create_extension_runtime()
        with pytest.raises(RuntimeError, match="not initialized"):
            runtime["sendMessage"]({"text": "hi"})

    def test_refresh_tools_is_noop(self):
        runtime = create_extension_runtime()
        runtime["refreshTools"]()

    def test_flag_values_starts_empty(self):
        runtime = create_extension_runtime()
        assert runtime["flagValues"] == {}

    def test_assert_active_passes_when_not_stale(self):
        runtime = create_extension_runtime()
        runtime["assertActive"]()

    def test_invalidate_sets_stale_message(self):
        runtime = create_extension_runtime()
        runtime["invalidate"]("stale!")
        with pytest.raises(RuntimeError, match="stale!"):
            runtime["assertActive"]()

    def test_register_provider_queues(self):
        runtime = create_extension_runtime()
        runtime["registerProvider"]("my-provider", {"baseUrl": "https://example.com"})
        assert len(runtime["pendingProviderRegistrations"]) == 1
        assert runtime["pendingProviderRegistrations"][0]["name"] == "my-provider"

    def test_unregister_provider_removes_from_queue(self):
        runtime = create_extension_runtime()
        runtime["registerProvider"]("p1", {})
        runtime["registerProvider"]("p2", {})
        runtime["unregisterProvider"]("p1")
        names = [r["name"] for r in runtime["pendingProviderRegistrations"]]
        assert "p1" not in names
        assert "p2" in names


class TestLoadExtensionFromFactory:
    async def test_loads_factory_and_registers_handlers(self):
        def factory(api):
            api["on"]("agent_start", lambda event, ctx: None)
            api["registerTool"]({"name": "my_tool", "label": "My", "description": "test"})

        runtime = create_extension_runtime()
        event_bus = {"on": lambda e, h: None, "emit": lambda e, *a: None}
        extension = await load_extension_from_factory(factory, "/tmp", event_bus, runtime)

        assert "agent_start" in extension["handlers"]
        assert len(extension["handlers"]["agent_start"]) == 1
        assert "my_tool" in extension["tools"]

    async def test_async_factory(self):
        async def factory(api):
            api["on"]("agent_end", lambda event, ctx: None)

        runtime = create_extension_runtime()
        event_bus = {"on": lambda e, h: None, "emit": lambda e, *a: None}
        extension = await load_extension_from_factory(factory, "/tmp", event_bus, runtime)
        assert "agent_end" in extension["handlers"]


class TestExtensionRunner:
    def _make_runner(self, extensions=None):
        runtime = create_extension_runtime()
        return ExtensionRunner(extensions or [], runtime, "/tmp")

    def test_has_handlers_false_when_empty(self):
        runner = self._make_runner()
        assert not runner.has_handlers("agent_start")

    def test_has_handlers_true(self):
        ext = {"path": "<test>", "handlers": {"agent_start": [lambda e, c: None]}}
        runner = self._make_runner([ext])
        assert runner.has_handlers("agent_start")

    def test_get_extension_paths(self):
        ext = {"path": "/tmp/ext.py", "handlers": {}}
        runner = self._make_runner([ext])
        assert runner.get_extension_paths() == ["/tmp/ext.py"]

    def test_get_all_registered_tools_dedupes(self):
        ext1 = {
            "path": "/tmp/ext1.py",
            "tools": {"tool_a": {"definition": {"name": "tool_a"}}},
            "handlers": {},
        }
        ext2 = {
            "path": "/tmp/ext2.py",
            "tools": {"tool_a": {"definition": {"name": "tool_a"}}, "tool_b": {"definition": {"name": "tool_b"}}},
            "handlers": {},
        }
        runner = self._make_runner([ext1, ext2])
        tools = runner.get_all_registered_tools()
        assert len(tools) == 2

    def test_get_tool_definition(self):
        ext = {"path": "/tmp/ext.py", "tools": {"my_tool": {"definition": {"name": "my_tool"}}}, "handlers": {}}
        runner = self._make_runner([ext])
        assert runner.get_tool_definition("my_tool") is not None
        assert runner.get_tool_definition("nonexistent") is None

    async def test_emit_calls_handlers(self):
        called = []

        def handler(event, ctx):
            called.append(event)

        ext = {"path": "<test>", "handlers": {"agent_start": [handler]}}
        runner = self._make_runner([ext])
        await runner.emit({"type": "agent_start"})
        assert len(called) == 1

    async def test_emit_session_before_cancel(self):
        def handler(event, ctx):
            return {"cancel": True}

        ext = {"path": "<test>", "handlers": {"session_before_switch": [handler]}}
        runner = self._make_runner([ext])
        result = await runner.emit({"type": "session_before_switch"})
        assert result is not None
        assert result.get("cancel") is True

    async def test_emit_tool_call_block(self):
        def handler(event, ctx):
            return {"block": True, "reason": "denied"}

        ext = {"path": "<test>", "handlers": {"tool_call": [handler]}}
        runner = self._make_runner([ext])
        result = await runner.emit_tool_call({"type": "tool_call", "toolName": "bash"})
        assert result is not None
        assert result.get("block") is True

    async def test_emit_tool_result_modifies_content(self):
        def handler(event, ctx):
            return {"content": [{"type": "text", "text": "modified"}]}

        ext = {"path": "<test>", "handlers": {"tool_result": [handler]}}
        runner = self._make_runner([ext])
        result = await runner.emit_tool_result({
            "type": "tool_result",
            "content": [{"type": "text", "text": "original"}],
        })
        assert result is not None
        assert result["content"][0]["text"] == "modified"

    async def test_emit_context_chains(self):
        def handler1(event, ctx):
            return {"messages": [{"role": "user", "content": "modified"}]}

        ext = {"path": "<test>", "handlers": {"context": [handler1]}}
        runner = self._make_runner([ext])
        result = await runner.emit_context([{"role": "user", "content": "original"}])
        assert result[0]["content"] == "modified"

    async def test_emit_input_transform(self):
        def handler(event, ctx):
            return {"action": "transform", "text": "transformed"}

        ext = {"path": "<test>", "handlers": {"input": [handler]}}
        runner = self._make_runner([ext])
        result = await runner.emit_input("hello", None, "interactive")
        assert result["action"] == "transform"
        assert result["text"] == "transformed"

    async def test_emit_input_handled(self):
        def handler(event, ctx):
            return {"action": "handled"}

        ext = {"path": "<test>", "handlers": {"input": [handler]}}
        runner = self._make_runner([ext])
        result = await runner.emit_input("hello", None, "interactive")
        assert result["action"] == "handled"

    async def test_emit_error_on_handler_failure(self):
        errors = []

        def bad_handler(event, ctx):
            raise RuntimeError("boom")

        ext = {"path": "<test>", "handlers": {"agent_start": [bad_handler]}}
        runner = self._make_runner([ext])
        runner.on_error(lambda e: errors.append(e))
        await runner.emit({"type": "agent_start"})
        assert len(errors) == 1
        assert "boom" in errors[0]["error"]

    async def test_emit_session_shutdown(self):
        from openclaw.agents.sessions.extensions import emit_session_shutdown_event

        called = []

        def handler(event, ctx):
            called.append(event)

        ext = {"path": "<test>", "handlers": {"session_shutdown": [handler]}}
        runner = self._make_runner([ext])
        result = await emit_session_shutdown_event(runner, {"type": "session_shutdown", "reason": "quit"})
        assert result is True
        assert len(called) == 1


class TestWrapRegisteredTool:
    def test_wrap_returns_agent_tool(self):
        async def execute(tool_call_id, params, signal, on_update, ctx):
            return {"content": []}

        registered = {
            "definition": {
                "name": "my_tool",
                "label": "My Tool",
                "description": "test",
                "execute": execute,
            }
        }
        runner = ExtensionRunner([], create_extension_runtime(), "/tmp")
        tool = wrap_registered_tool(registered, runner)
        assert tool["name"] == "my_tool"
        assert tool["label"] == "My Tool"

    def test_wrap_multiple_tools(self):
        registered_tools = [
            {"definition": {"name": "tool1", "label": "T1", "description": "", "execute": lambda *a: None}},
            {"definition": {"name": "tool2", "label": "T2", "description": "", "execute": lambda *a: None}},
        ]
        runner = ExtensionRunner([], create_extension_runtime(), "/tmp")
        tools = wrap_registered_tools(registered_tools, runner)
        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[1]["name"] == "tool2"
