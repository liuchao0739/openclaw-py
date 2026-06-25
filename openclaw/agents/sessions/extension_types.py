"""Minimal session extension types for agent hooks (subset of TS extensions/types)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from openclaw.llm.core import Message, Model

AgentMessage = Message | dict[str, Any]

E = TypeVar("E")
R = TypeVar("R")


@dataclass
class ContextEvent:
    messages: list[AgentMessage]
    type: str = "context"


@dataclass
class ExtensionContext:
    model: Model | None = None
    session_manager: object | None = None


class ExtensionAPI(Protocol):
    def on(
        self,
        event: str,
        handler: Callable[..., Any],
    ) -> None: ...


@dataclass
class SimpleExtensionAPI:
    """In-memory extension API for tests and lightweight hook registration."""

    _handlers: dict[str, list[Callable[..., Any]]] = field(default_factory=dict)

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        self._handlers.setdefault(event, []).append(handler)