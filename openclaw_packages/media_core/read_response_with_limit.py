from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from ..normalization_core.number_coercion import resolve_timer_timeout_ms


@dataclass(frozen=True)
class _ReadResponsePrefixResult:
    buffer: bytes
    size: int
    truncated: bool


async def _read_chunk_with_idle_timeout(
    reader: Any,
    chunk_timeout_ms: int,
    on_idle_timeout: Callable[[dict[str, int]], Exception] | None = None,
) -> Any:
    loop = asyncio.get_running_loop()
    resolved = resolve_timer_timeout_ms(chunk_timeout_ms, 1)
    timeout_exceeded = False

    future: asyncio.Future[Any] = loop.create_future()

    def _resolve(value: Any) -> None:
        if not timeout_exceeded and not future.done():
            future.set_result(value)

    def _reject(err: Any) -> None:
        if not timeout_exceeded and not future.done():
            if isinstance(err, BaseException):
                future.set_exception(err)
            else:
                future.set_exception(RuntimeError(str(err)))

    timer: asyncio.TimerHandle | None = None

    def _on_timeout() -> None:
        nonlocal timeout_exceeded
        timeout_exceeded = True
        error = (
            on_idle_timeout({"chunkTimeoutMs": resolved})
            if on_idle_timeout is not None
            else TimeoutError(f"Media download stalled: no data received for {resolved}ms")
        )
        try:
            cancel_fn = getattr(reader, "cancel", None)
            if callable(cancel_fn):
                result = cancel_fn(error)
                if hasattr(result, "catch"):
                    try:
                        result.catch(lambda _: None)
                    except Exception:
                        pass
                elif asyncio.iscoroutine(result):
                    try:
                        asyncio.create_task(result)
                    except Exception:
                        pass
        except Exception:
            pass
        if not future.done():
            future.set_exception(error)

    timer = loop.call_later(resolved / 1000.0, _on_timeout)

    try:
        read_coro = reader.read()
        result = await read_coro
        _resolve(result)
    except BaseException as err:
        _reject(err)
    finally:
        if timer is not None:
            timer.cancel()

    return await future


def _to_error_object(value: Any, fallback_message: str) -> Exception:
    if isinstance(value, Exception):
        return value
    if isinstance(value, str):
        return Exception(value)
    error = Exception(fallback_message)
    if isinstance(value, BaseException):
        return value
    try:
        if isinstance(value, (dict, list, tuple, set)):
            for k, v in value.items():
                setattr(error, str(k), v)
    except Exception:
        pass
    return error


async def _read_response_prefix(
    res: Any,
    max_bytes: int,
    chunk_timeout_ms: int | None = None,
    on_idle_timeout: Callable[[dict[str, int]], Exception] | None = None,
) -> _ReadResponsePrefixResult:
    body = getattr(res, "body", None)
    if body is None:
        read_async = getattr(res, "read", None)
        if read_async is None:
            read_async = getattr(res, "array_buffer", None)
        if read_async is None:
            raise ValueError("response has no readable body")
        data = await read_async()
        if isinstance(data, (bytes, bytearray, memoryview)):
            data = bytes(data)
        else:
            data = bytes(data)
        if len(data) > max_bytes:
            return _ReadResponsePrefixResult(
                buffer=data[:max_bytes], size=len(data), truncated=True
            )
        return _ReadResponsePrefixResult(buffer=data, size=len(data), truncated=False)

    has_reader = hasattr(body, "get_reader") or hasattr(body, "read")
    if not has_reader:
        read_async = getattr(res, "read", None) or getattr(res, "array_buffer", None)
        data = await read_async()
        if isinstance(data, (bytes, bytearray, memoryview)):
            data = bytes(data)
        else:
            data = bytes(data)
        if len(data) > max_bytes:
            return _ReadResponsePrefixResult(
                buffer=data[:max_bytes], size=len(data), truncated=True
            )
        return _ReadResponsePrefixResult(buffer=data, size=len(data), truncated=False)

    reader = body.get_reader() if hasattr(body, "get_reader") else body
    chunks: list[bytes] = []
    total = 0
    size = 0
    truncated = False
    try:
        while True:
            if chunk_timeout_ms is not None:
                result = await _read_chunk_with_idle_timeout(
                    reader, chunk_timeout_ms, on_idle_timeout
                )
            else:
                result = await reader.read()
            if result is None:
                size = total
                break
            if isinstance(result, tuple) and len(result) == 2:
                done, value = result
                if done:
                    size = total
                    break
                chunk = value
            else:
                chunk = result
                done = chunk is None
                if done:
                    size = total
                    break
            if chunk is None:
                size = total
                break
            if isinstance(chunk, (bytes, bytearray, memoryview)):
                value_bytes = bytes(chunk)
            else:
                value_bytes = bytes(chunk)
            if len(value_bytes) == 0:
                continue
            next_total = total + len(value_bytes)
            if next_total > max_bytes:
                remaining = max_bytes - total
                if remaining > 0:
                    chunks.append(value_bytes[:remaining])
                    total += remaining
                size = next_total
                truncated = True
                try:
                    cancel_fn = getattr(reader, "cancel", None)
                    if callable(cancel_fn):
                        await cancel_fn()
                except Exception:
                    pass
                break
            chunks.append(value_bytes)
            total = next_total
            size = total
    finally:
        release = getattr(reader, "release_lock", None)
        if callable(release):
            try:
                release()
            except Exception:
                pass

    return _ReadResponsePrefixResult(
        buffer=b"".join(chunks),
        size=size,
        truncated=truncated,
    )


async def read_response_with_limit(
    res: Any,
    max_bytes: int,
    on_overflow: Callable[[dict[str, Any]], Exception] | None = None,
    chunk_timeout_ms: int | None = None,
    on_idle_timeout: Callable[[dict[str, int]], Exception] | None = None,
) -> bytes:
    if on_overflow is None:
        def _default_overflow(params: dict[str, Any]) -> Exception:
            return ValueError(
                f"Content too large: {params['size']} bytes (limit: {params['maxBytes']} bytes)"
            )

        on_overflow = _default_overflow

    prefix = await _read_response_prefix(
        res, max_bytes, chunk_timeout_ms=chunk_timeout_ms, on_idle_timeout=on_idle_timeout
    )
    if prefix.truncated:
        raise on_overflow({"size": prefix.size, "maxBytes": max_bytes, "res": res})
    return prefix.buffer


async def read_response_text_snippet(
    res: Any,
    max_bytes: int | None = None,
    max_chars: int | None = None,
    chunk_timeout_ms: int | None = None,
    on_idle_timeout: Callable[[dict[str, int]], Exception] | None = None,
) -> str | None:
    if max_bytes is None:
        max_bytes = 8 * 1024
    if max_chars is None:
        max_chars = 200
    prefix = await _read_response_prefix(
        res, max_bytes, chunk_timeout_ms=chunk_timeout_ms, on_idle_timeout=on_idle_timeout
    )
    if len(prefix.buffer) == 0:
        return None
    try:
        text = prefix.buffer.decode("utf-8", errors="replace")
    except Exception:
        return None
    if not text:
        return None
    collapsed = " ".join(text.split()).strip()
    if not collapsed:
        return None
    if len(collapsed) > max_chars:
        return collapsed[:max_chars] + "\u2026"
    if prefix.truncated:
        return collapsed + "\u2026"
    return collapsed
