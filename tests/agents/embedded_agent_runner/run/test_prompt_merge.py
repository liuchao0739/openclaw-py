"""Tests for orphaned trailing user prompt merge."""

from openclaw.agents.embedded_agent_runner.run.attempt_prompt_helpers import (
    merge_orphaned_trailing_user_prompt,
    prompt_already_includes_queued_user_message,
    QUEUED_USER_MESSAGE_MARKER,
)
from openclaw.agents.embedded_agent_runner.run.message_merge_strategy import (
    resolve_message_merge_strategy,
)


def test_merge_orphaned_trailing_user():
    result = merge_orphaned_trailing_user_prompt(
        prompt="new turn",
        trigger="user",
        leaf_message={"content": "queued hello"},
    )
    assert result["merged"] is True
    assert result["removeLeaf"] is True
    assert QUEUED_USER_MESSAGE_MARKER in result["prompt"]
    assert "queued hello" in result["prompt"]
    assert result["prompt"].endswith("new turn")


def test_merge_skips_when_already_in_prompt():
    prompt = f"{QUEUED_USER_MESSAGE_MARKER}\nhello\n\nbody"
    result = merge_orphaned_trailing_user_prompt(
        prompt=prompt,
        trigger="user",
        leaf_message={"content": "hello"},
    )
    assert result["merged"] is False
    assert result["removeLeaf"] is True


def test_strategy_delegates_to_merge():
    strategy = resolve_message_merge_strategy()
    assert strategy["id"] == "orphan-trailing-user-prompt"
    out = strategy["mergeOrphanedTrailingUserPrompt"](
        prompt="x",
        trigger=None,
        leaf_message={"content": ""},
    )
    assert out["removeLeaf"] is True


def test_prompt_already_includes_orphan_inline():
    assert prompt_already_includes_queued_user_message("line\nhello\nmore", "hello") is True