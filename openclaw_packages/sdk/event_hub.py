from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Callable, Optional, TypeVar

from .types import GatewayEvent

T = TypeVar("T")


class EventHubOptions:
    def __init__(self, replay_limit: int = 0):
        self.replay_limit = replay_limit


class EventStreamOptions:
    def __init__(self, replay: bool = False):
        self.replay = replay


class EventHub:
    def __init__(self, options: Optional[EventHubOptions] = None):
        opts = options or EventHubOptions()
        self._replay_limit = opts.replay_limit
        self._replay_events: deque = deque()
        self._closed = False
        self._close_error: Any = None
        self._has_close_error = False
        self._listeners: set[Callable[[Any], None]] = set()
        self._waiters: set[asyncio.Future] = set()

    def publish(self, event: Any) -> None:
        if self._closed:
            return
        if self._replay_limit > 0:
            self._replay_events.append(event)
            overflow = len(self._replay_events) - self._replay_limit
            if overflow > 0:
                for _ in range(overflow):
                    self._replay_events.popleft()
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:
                pass

    def close(self, error: Any = None) -> None:
        if error is not None:
            self._close_error = error
            self._has_close_error = True
        self._closed = True
        self._replay_events.clear()
        self._listeners.clear()
        for wake in list(self._waiters):
            if not wake.done():
                wake.set_result(None)
        self._waiters.clear()

    def snapshot(self, filter: Optional[Callable[[Any], bool]] = None) -> list:
        if filter:
            return [e for e in self._replay_events if filter(e)]
        return list(self._replay_events)

    def stream(
        self,
        filter: Optional[Callable[[Any], bool]] = None,
        options: Optional[EventStreamOptions] = None,
    ) -> "EventStream":
        opts = options or EventStreamOptions()
        return EventStream(self, filter, opts)


class EventStream:
    def __init__(
        self,
        hub: EventHub,
        filter: Optional[Callable[[Any], bool]],
        options: EventStreamOptions,
    ):
        self._hub = hub
        self._filter = filter
        self._options = options
        self._queue: list = []
        self._stopped = False
        self._wake: Optional[asyncio.Future] = None
        self._listener: Optional[Callable[[Any], None]] = None
        self._iterator = self._async_iterator()

        if options.replay:
            self._queue = hub.snapshot(filter)

        def _listener(event: Any) -> None:
            if self._stopped:
                return
            if not filter or filter(event):
                self._queue.append(event)
                self._pending_wake()

        self._listener = _listener
        hub._listeners.add(_listener)

    def _pending_wake(self) -> None:
        if self._wake is None:
            return
        wake = self._wake
        self._wake = None
        self._hub._waiters.discard(wake)
        if not wake.done():
            wake.set_result(None)

    def _cleanup(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self._listener:
            self._hub._listeners.discard(self._listener)
            self._listener = None
        self._pending_wake()

    def __aiter__(self):
        return self._async_iterator()

    async def _async_iterator(self):
        try:
            while True:
                if self._stopped:
                    break
                if self._queue:
                    value = self._queue.pop(0)
                    yield value
                    continue
                if self._hub._closed:
                    break
                wake = asyncio.Future()
                self._wake = wake
                self._hub._waiters.add(wake)
                try:
                    await wake
                except asyncio.CancelledError:
                    break
            self._cleanup()
            if self._hub._has_close_error:
                raise self._hub._close_error
            return
        except GeneratorExit:
            self._cleanup()

    async def __anext__(self):
        async for item in self._async_iterator():
            return item
        raise StopAsyncIteration

    async def aclose(self):
        self._cleanup()


def is_gateway_event(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "event" in value
        and isinstance(value.get("event"), str)
    )
