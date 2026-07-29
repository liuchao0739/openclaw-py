"""Shared OpenAI-compatible `tool_choice` contract for the Chat Completions

Mirrors src/gateway/openai-tool-choice.ts.
"""

from __future__ import annotations

from typing import Any

ToolChoiceConstraint = Any

def tool_choice_constraint_prompt(*args: Any, **kwargs: Any) -> Any: ...
def is_tool_choice_constraint_satisfied(*args: Any, **kwargs: Any) -> Any: ...
def resolve_unsatisfied_tool_choice_message(*args: Any, **kwargs: Any) -> Any: ...
