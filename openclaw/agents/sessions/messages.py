"""Session message conversion bridge.

The canonical message conversion logic lives in the agent-core harness package.
This module provides a stable local import path for legacy session code.
"""

from __future__ import annotations

from typing import Any, TypedDict


class CustomMessage(TypedDict, total=False):
    customType: str
    content: Any
    display: Any
    details: Any


class BashExecutionMessage(TypedDict, total=False):
    role: str
    command: str
    output: str


class BranchSummaryMessage(TypedDict, total=False):
    role: str
    summary: str


class CompactionSummaryMessage(TypedDict, total=False):
    role: str
    summary: str


def convert_to_llm(messages: list[Any]) -> list[Any]:
    """Convert session messages to LLM format.

    Deferred to the agent-core harness package; this stub passes through
    messages unchanged during the migration window.
    """
    try:
        from openclaw_packages.agent_core.harness.messages import convert_to_llm as _convert

        return _convert(messages)
    except Exception:
        return messages
