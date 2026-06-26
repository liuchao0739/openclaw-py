"""Tests for tools, state, and status modules."""

from openclaw.tools.diagnostics import ToolPlanContractError
from openclaw.tools.protocol import to_tool_protocol_descriptor, to_tool_protocol_descriptors
from openclaw.state import resolve_openclaw_agent_sqlite_path
from openclaw.status import resolve_active_fallback_state


class TestToolPlanContractError:
    def test_creation(self):
        err = ToolPlanContractError(
            code="duplicate-tool-name",
            tool_name="search",
            message="Duplicate tool name",
        )
        assert err.code == "duplicate-tool-name"
        assert err.tool_name == "search"
        assert "Duplicate tool name" in str(err)


class TestToolProtocol:
    def test_to_descriptor(self):
        entry = {"descriptor": {"name": "search", "description": "Search tool", "inputSchema": {"type": "object"}}}
        result = to_tool_protocol_descriptor(entry)
        assert result.name == "search"
        assert result.description == "Search tool"
        assert result.input_schema == {"type": "object"}

    def test_to_descriptors(self):
        entries = [
            {"descriptor": {"name": "a", "description": "A", "inputSchema": {}}},
            {"descriptor": {"name": "b", "description": "B", "inputSchema": {}}},
        ]
        result = to_tool_protocol_descriptors(entries)
        assert len(result) == 2
        assert result[0].name == "a"


class TestStatePaths:
    def test_agent_sqlite_path(self):
        result = resolve_openclaw_agent_sqlite_path("main", {"OPENCLAW_STATE_DIR": "/tmp/state"})
        assert "agents" in result
        assert "main" in result
        assert "openclaw-agent.sqlite" in result

    def test_custom_path(self):
        result = resolve_openclaw_agent_sqlite_path("main", path="/custom/path.db")
        assert result == "/custom/path.db"

    def test_normalizes_agent_id(self):
        result = resolve_openclaw_agent_sqlite_path("My Agent", {"OPENCLAW_STATE_DIR": "/tmp"})
        assert "my-agent" in result


class TestFallbackNoticeState:
    def test_active_when_refs_differ_and_match_state(self):
        result = resolve_active_fallback_state(
            selected_model_ref="gpt-4",
            active_model_ref="gpt-3.5",
            state={
                "fallbackNoticeSelectedModel": "gpt-4",
                "fallbackNoticeActiveModel": "gpt-3.5",
                "fallbackNoticeReason": "unavailable",
            },
        )
        assert result["active"] is True
        assert result["reason"] == "unavailable"

    def test_inactive_when_refs_match(self):
        result = resolve_active_fallback_state(
            selected_model_ref="gpt-4",
            active_model_ref="gpt-4",
        )
        assert result["active"] is False

    def test_inactive_when_state_mismatch(self):
        result = resolve_active_fallback_state(
            selected_model_ref="gpt-4",
            active_model_ref="gpt-3.5",
            state={
                "fallbackNoticeSelectedModel": "claude",
                "fallbackNoticeActiveModel": "gpt-3.5",
            },
        )
        assert result["active"] is False

    def test_no_state(self):
        result = resolve_active_fallback_state("a", "b")
        assert result["active"] is False
