"""Tool-name matching helpers for context-pruning eligibility."""

from __future__ import annotations

from collections.abc import Callable

from openclaw.agents.agent_hooks.context_pruning.settings import ContextPruningToolMatch
from openclaw.agents.glob_pattern import compile_glob_patterns, matches_any_glob_pattern


def _normalize_glob(value: str) -> str:
    return (value or "").strip().lower()


def make_tool_prunable_predicate(
    match: ContextPruningToolMatch,
) -> Callable[[str], bool]:
    deny = compile_glob_patterns(raw=match.deny, normalize=_normalize_glob)
    allow = compile_glob_patterns(raw=match.allow, normalize=_normalize_glob)

    def predicate(tool_name: str) -> bool:
        normalized = _normalize_glob(tool_name)
        if matches_any_glob_pattern(normalized, deny):
            return False
        if not allow:
            return True
        return matches_any_glob_pattern(normalized, allow)

    return predicate