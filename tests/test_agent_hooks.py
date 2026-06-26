"""Tests for agents/agent-hooks modules."""

from openclaw.agents.agent_hooks import (
    DEFAULT_COMPACTION_INSTRUCTIONS,
    MAX_INSTRUCTION_LENGTH,
    resolve_compaction_instructions,
    compose_split_turn_instructions,
    DEFAULT_CONTEXT_PRUNING_SETTINGS,
    compute_effective_settings,
    prune_context_messages,
    SessionManagerRuntimeRegistry,
    create_session_manager_runtime_registry,
)


class TestCompactionInstructions:
    def test_default(self):
        assert "language" in DEFAULT_COMPACTION_INSTRUCTIONS

    def test_event_takes_precedence(self):
        result = resolve_compaction_instructions("event-instr", "runtime-instr")
        assert result == "event-instr"

    def test_runtime_fallback(self):
        result = resolve_compaction_instructions(None, "runtime-instr")
        assert result == "runtime-instr"

    def test_default_fallback(self):
        result = resolve_compaction_instructions(None, None)
        assert result == DEFAULT_COMPACTION_INSTRUCTIONS

    def test_empty_string_falls_through(self):
        result = resolve_compaction_instructions("  ", "runtime")
        assert result == "runtime"

    def test_truncation(self):
        long = "x" * (MAX_INSTRUCTION_LENGTH + 100)
        result = resolve_compaction_instructions(long, None)
        assert len(result) == MAX_INSTRUCTION_LENGTH

    def test_compose(self):
        result = compose_split_turn_instructions("prefix", "resolved")
        assert "prefix" in result
        assert "resolved" in result
        assert "Additional requirements:" in result


class TestContextPruning:
    def test_disabled_returns_all(self):
        msgs = [{"role": "user", "content": "1"}, {"role": "user", "content": "2"}]
        result = prune_context_messages(msgs, {"enabled": False})
        assert len(result) == 2

    def test_prune_to_max(self):
        msgs = [{"role": "user", "content": str(i)} for i in range(10)]
        result = prune_context_messages(msgs, {"enabled": True, "maxMessages": 3})
        assert len(result) == 3
        assert result[0]["content"] == "7"

    def test_preserve_system(self):
        msgs = [{"role": "system", "content": "sys"}]
        msgs += [{"role": "user", "content": str(i)} for i in range(10)]
        result = prune_context_messages(msgs, {"enabled": True, "maxMessages": 3, "preserveSystemMessages": True})
        assert result[0]["role"] == "system"
        assert len(result) == 4

    def test_preserve_tools(self):
        msgs = [{"role": "tool", "content": "tool1"}]
        msgs += [{"role": "user", "content": str(i)} for i in range(10)]
        result = prune_context_messages(msgs, {"enabled": True, "maxMessages": 3, "preserveToolCalls": True})
        assert result[0]["role"] == "tool"

    def test_zero_max(self):
        msgs = [{"role": "user", "content": "1"}]
        result = prune_context_messages(msgs, {"enabled": True, "maxMessages": 0})
        assert len(result) == 1

    def test_compute_effective_settings(self):
        result = compute_effective_settings({"maxMessages": 5}, {"enabled": True})
        assert result["maxMessages"] == 5
        assert result["enabled"] is True
        assert result["preserveSystemMessages"] is True

    def test_default_settings(self):
        assert DEFAULT_CONTEXT_PRUNING_SETTINGS["enabled"] is False


class TestSessionManagerRegistry:
    def test_set_get(self):
        reg = SessionManagerRuntimeRegistry()
        obj = object()
        reg.set(obj, "value")
        assert reg.get(obj) == "value"

    def test_get_missing(self):
        reg = SessionManagerRuntimeRegistry()
        assert reg.get(object()) is None

    def test_set_none_deletes(self):
        reg = SessionManagerRuntimeRegistry()
        obj = object()
        reg.set(obj, "value")
        reg.set(obj, None)
        assert reg.get(obj) is None

    def test_set_none_no_crash(self):
        reg = SessionManagerRuntimeRegistry()
        reg.set(None, "value")

    def test_get_none(self):
        reg = SessionManagerRuntimeRegistry()
        assert reg.get(None) is None

    def test_factory(self):
        reg = create_session_manager_runtime_registry()
        assert isinstance(reg, SessionManagerRuntimeRegistry)
