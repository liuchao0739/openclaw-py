"""AbortSignal-aware promise racing helper for embedded-agent attempts."""

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


class AbortError(Exception):
    def __init__(self, message: str = "aborted", *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.name = "AbortError"
        if cause is not None:
            self.__cause__ = cause


def _to_lint_error_object(value: object, fallback_message: str) -> Exception:
    if isinstance(value, BaseException):
        return value
    if isinstance(value, str):
        return Exception(value)
    return Exception(fallback_message)


async def abortable(signal: asyncio.Event | None, promise: Awaitable[T]) -> T:
    """Race an awaitable against an abort event (asyncio.Event as AbortSignal stand-in)."""
    if signal is not None and signal.is_set():
        raise AbortError("aborted")

    async def _run() -> T:
        try:
            return await promise
        except BaseException as err:
            raise _to_lint_error_object(err, "Non-Error rejection") from err

    if signal is None:
        return await _run()

    task = asyncio.create_task(_run())
    abort_wait = asyncio.create_task(signal.wait())

    done, pending = await asyncio.wait(
        {task, abort_wait},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for p in pending:
        p.cancel()
        try:
            await p
        except asyncio.CancelledError:
            pass

    if abort_wait in done and signal.is_set():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        raise AbortError("aborted")

    return await task