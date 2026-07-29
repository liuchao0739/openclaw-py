import asyncio
from typing import Any, AsyncIterator, Callable, Generic, List, Optional, TypeVar

from ..types import AssistantMessage, AssistantMessageEvent

T = TypeVar("T")
R = TypeVar("R")

_DONE_SENTINEL = object()


class EventStream(Generic[T, R]):
    def __init__(self, is_complete: Callable[[T], bool], extract_result: Callable[[T], R]):
        self._queue: List[T] = []
        self._waiting: List[Any] = []
        self._done = False
        self._is_complete = is_complete
        self._extract_result = extract_result
        self._final_result_future: Optional[asyncio.Future] = None
        self._final_result_value: Any = None
        self._final_result_set = False

    def _resolve_final_result(self, result: R) -> None:
        self._final_result_value = result
        self._final_result_set = True
        if self._final_result_future is not None and not self._final_result_future.done():
            self._final_result_future.set_result(result)

    def push(self, event: T) -> None:
        if self._done:
            return
        if self._is_complete(event):
            self._done = True
            self._resolve_final_result(self._extract_result(event))
        if self._waiting:
            future = self._waiting.pop(0)
            if not future.done():
                future.set_result(event)
        else:
            self._queue.append(event)

    def end(self, result: Optional[R] = None) -> None:
        self._done = True
        if result is not None:
            self._resolve_final_result(result)
        while self._waiting:
            future = self._waiting.pop(0)
            if not future.done():
                future.set_result(_DONE_SENTINEL)

    def __aiter__(self) -> "EventStream[T, R]":
        return self

    async def __anext__(self) -> T:
        if self._queue:
            return self._queue.pop(0)
        if self._done:
            raise StopAsyncIteration
        future = asyncio.get_running_loop().create_future()
        self._waiting.append(future)
        result = await future
        if result is _DONE_SENTINEL:
            raise StopAsyncIteration
        return result

    async def result(self) -> R:
        if self._final_result_set:
            return self._final_result_value
        if self._final_result_future is None:
            self._final_result_future = asyncio.get_running_loop().create_future()
        return await self._final_result_future


class AssistantMessageEventStream(EventStream[AssistantMessageEvent, AssistantMessage]):
    def __init__(self):
        def is_complete(event: AssistantMessageEvent) -> bool:
            return event.get("type") in ("done", "error")

        def extract_result(event: AssistantMessageEvent) -> AssistantMessage:
            if event.get("type") == "done":
                return event.get("message")
            elif event.get("type") == "error":
                return event.get("error")
            raise ValueError("Unexpected event type for final result")

        super().__init__(is_complete, extract_result)


def create_assistant_message_event_stream() -> AssistantMessageEventStream:
    return AssistantMessageEventStream()
