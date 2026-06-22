"""Tests compaction instruction defaults and precedence."""

from openclaw.agents.agent_hooks.compaction_instructions import (
    DEFAULT_COMPACTION_INSTRUCTIONS,
    compose_split_turn_instructions,
    resolve_compaction_instructions,
)


def test_default_non_empty():
    assert DEFAULT_COMPACTION_INSTRUCTIONS.strip()
    assert "primary language" in DEFAULT_COMPACTION_INSTRUCTIONS


def test_resolve_precedence():
    assert resolve_compaction_instructions(None, None) == DEFAULT_COMPACTION_INSTRUCTIONS
    assert resolve_compaction_instructions("", "runtime value") == "runtime value"
    assert resolve_compaction_instructions("   ", "runtime value") == "runtime value"
    assert resolve_compaction_instructions(None, "") == DEFAULT_COMPACTION_INSTRUCTIONS


def test_compose_split_turn():
    out = compose_split_turn_instructions("prefix", "resolved")
    assert "prefix" in out
    assert "resolved" in out