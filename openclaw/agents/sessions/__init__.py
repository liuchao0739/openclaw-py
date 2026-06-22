"""Session extension API (minimal port for agent hooks)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from openclaw.agents.agent_hooks.context_pruning.pruner import AgentMessage
from openclaw.llm.core import Model


@dataclass
class ContextEvent:
    messages: list[AgentMessage]


@dataclass
class ExtensionContext:
    model: Model | None = None
    session_manager: object | None = None


ContextHandler = Callable[
    [ContextEvent, ExtensionContext],
    dict[str, list[AgentMessage]] | None,
]


class ExtensionAPI(Protocol):
    def on(self, name: str, fn: ContextHandler) -> None: ...


@dataclass
class SimpleExtensionAPI:
    """Collects extension handlers until a full session runtime exists."""

    _handlers: dict[str, list[Any]] = field(default_factory=dict)

    def on(self, name: str, fn: Any) -> None:
        self._handlers.setdefault(name, []).append(fn)