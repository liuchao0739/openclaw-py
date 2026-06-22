"""Reconciles orphaned trailing user prompts before provider submission."""

from __future__ import annotations

from typing import Any, Callable, Literal, TypedDict

from openclaw.agents.embedded_agent_runner.run.attempt_prompt_helpers import (
    merge_orphaned_trailing_user_prompt,
)
from openclaw.agents.embedded_agent_runner.run.params import EmbeddedRunTrigger

MessageMergeStrategyId = Literal["orphan-trailing-user-prompt"]

DEFAULT_MESSAGE_MERGE_STRATEGY_ID: MessageMergeStrategyId = "orphan-trailing-user-prompt"


class MessageMergeStrategy(TypedDict):
    id: MessageMergeStrategyId
    mergeOrphanedTrailingUserPrompt: Callable[..., dict[str, Any]]


_default_strategy: MessageMergeStrategy = {
    "id": DEFAULT_MESSAGE_MERGE_STRATEGY_ID,
    "mergeOrphanedTrailingUserPrompt": merge_orphaned_trailing_user_prompt,
}

_active_strategy: MessageMergeStrategy = _default_strategy


def resolve_message_merge_strategy() -> MessageMergeStrategy:
    return _active_strategy


def register_message_merge_strategy_for_test(strategy: MessageMergeStrategy) -> Callable[[], None]:
    global _active_strategy
    previous = _active_strategy
    _active_strategy = strategy

    def restore() -> None:
        global _active_strategy
        _active_strategy = previous

    return restore