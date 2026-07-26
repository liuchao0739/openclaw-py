"""Assistant message event streams (ported subset from packages/llm-core)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal, TypeVar

from openclaw.llm.core import AssistantMessage, ToolCall

T = TypeVar("T")
R = TypeVar("R")

StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


class EventStream:
    """Generic async-iterable event stream with a separately awaited final result."""

    def __init__(
        self,
        is_complete: Callable[[T], bool],
        extract_result: Callable[[T], R],
    ) -> None:
        self._queue: list[T] = []
        self._waiting: list[asyncio.Future[tuple[T | None, bool]]] = []
        self._done = False
        self._result_future: asyncio.Future[R] = asyncio.Future()
        self._is_complete = is_complete
        self._extract_result = extract_result

    def push(self, event: T) -> None:
        if self._done:
            return

        if self._is_complete(event):
            self._done = True
            if not self._result_future.done():
                self._result_future.set_result(self._extract_result(event))

        if self._waiting:
            waiter = self._waiting.pop(0)
            if not waiter.done():
                waiter.set_result((event, False))
        else:
            self._queue.append(event)

    def end(self, result: R | None = None) -> None:
        self._done = True
        if result is not None and not self._result_future.done():
            self._result_future.set_result(result)
        while self._waiting:
            waiter = self._waiting.pop(0)
            if not waiter.done():
                waiter.set_result((None, True))

    def __aiter__(self) -> AsyncIterator[T]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[T]:
        while True:
            if self._queue:
                yield self._queue.pop(0)
            elif self._done:
                return
            else:
                loop = asyncio.get_running_loop()
                waiter: asyncio.Future[tuple[T | None, bool]] = loop.create_future()
                self._waiting.append(waiter)
                value, done = await waiter
                if done:
                    return
                if value is not None:
                    yield value

    async def result(self) -> R:
        return await self._result_future


AssistantMessageEvent = dict[str, Any]


class AssistantMessageEventStream(EventStream):
    """Assistant-message event stream that resolves on done/error terminal events."""

    def __init__(self) -> None:
        super().__init__(
            lambda event: event.get("type") in ("done", "error"),
            _extract_assistant_message_result,
        )


def _extract_assistant_message_result(event: AssistantMessageEvent) -> AssistantMessage:
    event_type = event.get("type")
    if event_type == "done":
        return event["message"]
    if event_type == "error":
        return event["error"]
    raise ValueError("Unexpected event type for final result")


def create_assistant_message_event_stream() -> AssistantMessageEventStream:
    """Create an assistant-message stream for provider and plugin adapters."""
    return AssistantMessageEventStream()


__all__ = [
    "AssistantMessageEvent",
    "AssistantMessageEventStream",
    "EventStream",
    "StopReason",
    "ToolCall",
    "create_assistant_message_event_stream",
]
