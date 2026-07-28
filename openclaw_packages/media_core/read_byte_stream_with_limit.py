from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ByteStreamLimitOverflow:
    size: int
    max_bytes: int


def _normalize_byte_chunk(chunk: Any) -> bytes:
    if isinstance(chunk, (bytes, bytearray, memoryview)):
        if isinstance(chunk, (bytearray, memoryview)):
            return bytes(chunk)
        return bytes(chunk)
    if isinstance(chunk, str):
        return chunk.encode("utf-8")
    if isinstance(chunk, (bytes,)):
        return chunk
    if hasattr(chunk, "tobytes"):
        try:
            return chunk.tobytes()
        except Exception:
            pass
    if hasattr(chunk, "buffer") and hasattr(chunk, "byte_offset") and hasattr(chunk, "byte_length"):
        try:
            return bytes(memoryview(chunk.buffer)[chunk.byte_offset : chunk.byte_offset + chunk.byte_length])
        except Exception:
            pass
    raise TypeError(f"Unsupported byte stream chunk: {type(chunk).__name__}")


def _destroy_readable_on_overflow(stream: Any, err: Exception) -> None:
    destroy = getattr(stream, "destroy", None)
    if callable(destroy):
        try:
            destroy(err)
        except Exception:
            pass
        return
    cancel = getattr(stream, "cancel", None)
    if callable(cancel):
        try:
            cancel(err)
        except Exception:
            pass


async def read_byte_stream_with_limit(
    stream: AsyncIterator[Any],
    max_bytes: int,
    on_overflow: Callable[[ByteStreamLimitOverflow], Exception] | None = None,
) -> bytes:
    if not float(max_bytes).is_integer() or max_bytes < 0:
        raise ValueError(f"maxBytes must be a non-negative finite number: {max_bytes}")

    if on_overflow is None:
        def _default_overflow(params: ByteStreamLimitOverflow) -> Exception:
            return ValueError(
                f"Content too large: {params.size} bytes (limit: {params.max_bytes} bytes)"
            )

        on_overflow = _default_overflow

    chunks: list[bytes] = []
    total = 0

    async for chunk in stream:
        buffer = _normalize_byte_chunk(chunk)
        if len(buffer) == 0:
            continue
        next_total = total + len(buffer)
        if next_total > max_bytes:
            err = on_overflow(ByteStreamLimitOverflow(size=next_total, max_bytes=max_bytes))
            _destroy_readable_on_overflow(stream, err)
            raise err
        chunks.append(buffer)
        total = next_total

    return b"".join(chunks)
