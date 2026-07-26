"""Provider HTTP helpers for bounded response reads and provider operations."""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

PROVIDER_TEXT_RESPONSE_MAX_BYTES = 16 * 1024 * 1024
DEFAULT_GUARDED_HTTP_TIMEOUT_MS = 60_000

ProviderOperationTimeoutMs = int | Callable[[], int]


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


@dataclass
class ProviderOperationDeadline:
    label: str
    deadline_at_ms: int | None = None
    timeout_ms: int | None = None


def _resolve_timer_timeout_ms(timeout_ms: Any, minimum: int = 1) -> int:
    if not isinstance(timeout_ms, (int, float)) or not math.isfinite(timeout_ms) or timeout_ms <= 0:
        return minimum
    return max(minimum, int(timeout_ms))


def create_provider_operation_deadline(
    *,
    timeout_ms: int | None = None,
    label: str,
) -> ProviderOperationDeadline:
    """Create a timer-safe absolute operation deadline from an optional total timeout."""
    if timeout_ms is None:
        return ProviderOperationDeadline(label=label)
    resolved = _resolve_timer_timeout_ms(timeout_ms)
    return ProviderOperationDeadline(
        label=label,
        timeout_ms=resolved,
        deadline_at_ms=int(time.time() * 1000) + resolved,
    )


def resolve_provider_operation_timeout_ms(
    *,
    deadline: ProviderOperationDeadline,
    default_timeout_ms: int,
) -> int:
    """Resolve a per-request timeout without exceeding the remaining operation deadline."""
    default_timeout = _resolve_timer_timeout_ms(default_timeout_ms)
    if deadline.deadline_at_ms is None:
        return default_timeout
    remaining_ms = deadline.deadline_at_ms - int(time.time() * 1000)
    if remaining_ms <= 0:
        raise ValueError(f"{deadline.label} timed out after {deadline.timeout_ms}ms")
    return max(1, min(default_timeout, remaining_ms))


def create_provider_operation_timeout_resolver(
    *,
    deadline: ProviderOperationDeadline,
    default_timeout_ms: int,
) -> Callable[[], int]:
    """Return a lazy timeout resolver for polling/retry HTTP call paths."""
    return lambda: resolve_provider_operation_timeout_ms(
        deadline=deadline,
        default_timeout_ms=default_timeout_ms,
    )


async def wait_provider_operation_poll_interval(
    *,
    deadline: ProviderOperationDeadline,
    poll_interval_ms: int,
) -> None:
    """Wait for the next poll interval while respecting the total operation deadline."""
    interval = _resolve_timer_timeout_ms(poll_interval_ms)
    if deadline.deadline_at_ms is None:
        await asyncio.sleep(interval / 1000)
        return
    remaining_ms = deadline.deadline_at_ms - int(time.time() * 1000)
    if remaining_ms <= 0:
        raise ValueError(f"{deadline.label} timed out after {deadline.timeout_ms}ms")
    await asyncio.sleep(min(interval, remaining_ms) / 1000)


def _resolve_provider_operation_request_timeout_ms(
    timeout_ms: ProviderOperationTimeoutMs | None,
) -> int:
    resolved = timeout_ms() if callable(timeout_ms) else timeout_ms
    if not isinstance(resolved, (int, float)) or not math.isfinite(resolved) or resolved <= 0:
        return DEFAULT_GUARDED_HTTP_TIMEOUT_MS
    return int(resolved)


async def fetch_with_timeout(
    url: str,
    init: dict[str, Any],
    timeout_ms: int,
    fetch_fn: Callable[..., Awaitable[Any]],
) -> Any:
    """Fetch a URL with a timeout using the provided fetch implementation."""
    return await asyncio.wait_for(
        fetch_fn(url, init),
        timeout=max(1, timeout_ms) / 1000,
    )


class _FetchResponse:
    def __init__(self, response: Any) -> None:
        self.ok = bool(getattr(response, "is_success", getattr(response, "ok", False)))
        self.status = getattr(response, "status_code", getattr(response, "status", 0))
        self.headers = getattr(response, "headers", {})
        self._response = response

    async def json(self) -> Any:
        if hasattr(self._response, "json"):
            result = self._response.json()
            if asyncio.iscoroutine(result):
                return await result
            return result
        raise AttributeError("response has no json()")


async def default_fetch_fn(url: str, init: dict[str, Any]) -> _FetchResponse:
    """Default fetch implementation backed by httpx when available."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.request(
            init.get("method", "GET"),
            url,
            headers=init.get("headers"),
            content=init.get("body"),
        )
    return _FetchResponse(response)


async def assert_ok_or_throw_http_error(response: Any, label: str) -> None:
    """Raise when a provider HTTP response is not successful."""
    if getattr(response, "ok", True):
        return
    status = getattr(response, "status", "unknown")
    raise RuntimeError(f"{label}: HTTP {status}")


async def execute_provider_operation_with_retry(
    *,
    operation: Callable[[], Awaitable[Any]],
    **_kwargs: Any,
) -> Any:
    """Execute a provider operation, retrying transient failures when configured."""
    return await operation()


async def fetch_provider_operation_response(params: dict[str, Any]) -> Any:
    """Fetch a provider operation response with optional HTTP error assertion."""
    timeout_ms = _resolve_provider_operation_request_timeout_ms(params.get("timeoutMs"))
    response = await execute_provider_operation_with_retry(
        stage=params.get("stage"),
        operation=lambda: fetch_with_timeout(
            params["url"],
            params.get("init") or {},
            timeout_ms,
            params["fetchFn"],
        ),
    )
    request_failed_message = params.get("requestFailedMessage")
    if request_failed_message:
        await assert_ok_or_throw_http_error(response, request_failed_message)
    return response


async def fetch_provider_download_response(params: dict[str, Any]) -> Any:
    """Download a provider asset response with HTTP error assertion."""
    return await fetch_provider_operation_response(
        {
            "stage": "download",
            "url": params["url"],
            "init": params.get("init"),
            "timeoutMs": params.get("timeoutMs"),
            "fetchFn": params["fetchFn"],
            "provider": params.get("provider"),
            "requestFailedMessage": params["requestFailedMessage"],
            "retry": params.get("retry"),
        }
    )


def resolve_provider_http_request_config(params: dict[str, Any]) -> dict[str, Any]:
    """Resolve provider HTTP base URL, headers, and transport policy inputs."""
    base_url = params.get("baseUrl") or params.get("defaultBaseUrl")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("Missing baseUrl: provide baseUrl or defaultBaseUrl")
    headers: dict[str, str] = {}
    default_headers = params.get("defaultHeaders")
    if isinstance(default_headers, dict):
        headers.update({str(key): str(value) for key, value in default_headers.items()})
    caller_headers = params.get("headers")
    if isinstance(caller_headers, dict):
        headers.update({str(key): str(value) for key, value in caller_headers.items()})
    elif caller_headers is not None:
        headers.update(dict(caller_headers))
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    allow_private_network = (
        params.get("allowPrivateNetwork") is True or request.get("allowPrivateNetwork") is True
    )
    return {
        "baseUrl": base_url.strip(),
        "allowPrivateNetwork": allow_private_network,
        "headers": headers,
        "dispatcherPolicy": None,
    }


async def post_json_request(params: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to a provider endpoint and return the response plus release hook."""
    timeout_ms = params.get("timeoutMs", DEFAULT_GUARDED_HTTP_TIMEOUT_MS)
    response = await fetch_with_timeout(
        params["url"],
        {
            "method": "POST",
            "headers": params.get("headers") or {},
            "body": json.dumps(params.get("body") or {}),
        },
        _resolve_provider_operation_request_timeout_ms(timeout_ms),
        params["fetchFn"],
    )

    async def release() -> None:
        return None

    return {"response": response, "release": release}
