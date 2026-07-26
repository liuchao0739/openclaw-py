"""Provider HTTP helpers for bounded response reads."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Protocol

PROVIDER_TEXT_RESPONSE_MAX_BYTES = 16 * 1024 * 1024


class _StreamReader(Protocol):
    async def read(self) -> tuple[bytes, bool]: ...

    async def cancel(self) -> None: ...


class _ReadableBody(Protocol):
    def get_reader(self) -> _StreamReader: ...


class _TextReadableResponse(Protocol):
    @property
    def body(self) -> _ReadableBody | None: ...

    async def text(self) -> str: ...

    async def aread(self) -> bytes: ...


async def read_response_with_limit(
    response: _TextReadableResponse,
    max_bytes: int,
    *,
    on_overflow: Callable[[dict[str, int]], Exception] | None = None,
) -> bytes:
    """Read a response body up to max_bytes, raising on_overflow when truncated."""
    body = getattr(response, "body", None)
    reader = body.get_reader() if body is not None and hasattr(body, "get_reader") else None
    if reader is not None and max_bytes > 0:
        parts: list[bytes] = []
        bytes_read = 0
        truncated = False
        try:
            while True:
                chunk, done = await reader.read()
                if done:
                    break
                if not chunk:
                    continue
                if bytes_read + len(chunk) > max_bytes:
                    remaining = max(0, max_bytes - bytes_read)
                    if remaining <= 0:
                        truncated = True
                        break
                    chunk = chunk[:remaining]
                    truncated = True
                bytes_read += len(chunk)
                parts.append(chunk)
                if truncated or bytes_read >= max_bytes:
                    truncated = True
                    break
        finally:
            if truncated:
                with contextlib.suppress(Exception):
                    await reader.cancel()

        if truncated and bytes_read >= max_bytes:
            overflow = (
                on_overflow({"maxBytes": max_bytes})
                if on_overflow
                else ValueError(f"response exceeds {max_bytes} bytes")
            )
            raise overflow

        return b"".join(parts)

    if hasattr(response, "aiter_bytes"):
        parts = []
        bytes_read = 0
        truncated = False
        async for chunk in response.aiter_bytes():
            if not chunk:
                continue
            if bytes_read + len(chunk) > max_bytes:
                remaining = max(0, max_bytes - bytes_read)
                if remaining <= 0:
                    truncated = True
                    break
                chunk = chunk[:remaining]
                truncated = True
            bytes_read += len(chunk)
            parts.append(chunk)
            if truncated or bytes_read >= max_bytes:
                truncated = True
                break
        if truncated and bytes_read >= max_bytes:
            overflow = (
                on_overflow({"maxBytes": max_bytes})
                if on_overflow
                else ValueError(f"response exceeds {max_bytes} bytes")
            )
            raise overflow
        return b"".join(parts)

    if hasattr(response, "aread"):
        data = await response.aread()
        if len(data) > max_bytes:
            overflow = (
                on_overflow({"maxBytes": max_bytes})
                if on_overflow
                else ValueError(f"response exceeds {max_bytes} bytes")
            )
            raise overflow
        return data

    text = await response.text()
    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        overflow = (
            on_overflow({"maxBytes": max_bytes})
            if on_overflow
            else ValueError(f"response exceeds {max_bytes} bytes")
        )
        raise overflow
    return encoded


async def read_provider_text_response(
    response: _TextReadableResponse,
    label: str,
    *,
    max_bytes: int | None = None,
) -> str:
    """Read a successful provider text response under a byte cap."""
    limit = max_bytes if max_bytes is not None else PROVIDER_TEXT_RESPONSE_MAX_BYTES
    body = getattr(response, "body", None)
    reader = body.get_reader() if body is not None and hasattr(body, "get_reader") else None
    if reader is not None and limit > 0:
        parts: list[bytes] = []
        bytes_read = 0
        truncated = False
        try:
            while True:
                chunk, done = await reader.read()
                if done:
                    break
                if not chunk:
                    continue
                if bytes_read + len(chunk) > limit:
                    remaining = max(0, limit - bytes_read)
                    if remaining <= 0:
                        truncated = True
                        break
                    chunk = chunk[:remaining]
                    truncated = True
                bytes_read += len(chunk)
                parts.append(chunk)
                if truncated or bytes_read >= limit:
                    truncated = True
                    break
        finally:
            if truncated:
                with contextlib.suppress(Exception):
                    await reader.cancel()

        if truncated and bytes_read >= limit:
            raise ValueError(f"{label}: text response exceeds {limit} bytes")

        return b"".join(parts).decode("utf-8", errors="replace")

    if hasattr(response, "aread"):
        data = await response.aread()
        if len(data) > limit:
            raise ValueError(f"{label}: text response exceeds {limit} bytes")
        return data.decode("utf-8", errors="replace")

    text = await response.text()
    encoded_len = len(text.encode("utf-8"))
    if encoded_len > limit:
        raise ValueError(f"{label}: text response exceeds {limit} bytes")
    return text
