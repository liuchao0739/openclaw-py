"""Tests for Chutes OAuth login flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw_extensions.chutes.api import login_chutes


class _ReadableBody:
    def __init__(self, data: bytes) -> None:
        self._reader = _StreamReader(data)

    def get_reader(self) -> _StreamReader:
        return self._reader


class _StreamReader:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self._read = False
        self.cancel = AsyncMock()
        self.release_lock = AsyncMock()

    async def read(self) -> tuple[bytes, bool]:
        if self._read:
            return b"", True
        self._read = True
        return self._body, False


class _BoundedErrorResponse:
    def __init__(self, body: bytes, status: int = 500) -> None:
        self.ok = False
        self.status = status
        self.headers: dict[str, str] = {}
        self.body = _ReadableBody(body)
        self.text = AsyncMock(side_effect=RuntimeError("response.text() should not be called"))


def _bounded_error_response(body: str, status: int = 500) -> _BoundedErrorResponse:
    return _BoundedErrorResponse(body.encode("utf-8"), status=status)


@pytest.mark.asyncio
async def test_rejects_unsafe_token_lifetimes_before_storing_credentials() -> None:
    async def fetch_fn(url: str, _init: dict[str, Any] | None = None) -> Any:
        if url == "https://api.chutes.ai/idp/token":
            return _MockJsonResponse(
                {
                    "access_token": "at_unsafe",
                    "refresh_token": "rt_unsafe",
                    "expires_in": 1e309,
                }
            )
        return _MockJsonResponse(status=404, payload="not found")

    with pytest.raises(RuntimeError, match="Chutes token exchange returned invalid expires_in"):
        await login_chutes(
            {
                "app": {
                    "clientId": "cid_test",
                    "redirectUri": "http://127.0.0.1:1456/oauth-callback",
                    "scopes": ["openid"],
                },
                "manual": True,
                "createState": lambda: "state_test",
                "onAuth": AsyncMock(),
                "onPrompt": AsyncMock(
                    return_value=(
                        "http://127.0.0.1:1456/oauth-callback?code=code_test&state=state_test"
                    )
                ),
                "fetchFn": fetch_fn,
            }
        )


@pytest.mark.asyncio
async def test_bounds_token_exchange_error_bodies_without_requiring_response_text() -> None:
    error_response = _bounded_error_response(
        f"{'chutes token unavailable ' * 1024}tail-marker",
        status=502,
    )

    async def fetch_fn(url: str, _init: dict[str, Any] | None = None) -> Any:
        if url == "https://api.chutes.ai/idp/token":
            return error_response
        return _MockJsonResponse(status=404, payload="not found")

    with pytest.raises(RuntimeError) as exc_info:
        await login_chutes(
            {
                "app": {
                    "clientId": "cid_test",
                    "redirectUri": "http://127.0.0.1:1456/oauth-callback",
                    "scopes": ["openid"],
                },
                "manual": True,
                "createState": lambda: "state_test",
                "onAuth": AsyncMock(),
                "onPrompt": AsyncMock(
                    return_value=(
                        "http://127.0.0.1:1456/oauth-callback?code=code_test&state=state_test"
                    )
                ),
                "fetchFn": fetch_fn,
            }
        )

    message = str(exc_info.value)
    assert "Chutes token exchange failed: chutes token unavailable" in message
    assert "tail-marker" not in message
    error_response.text.assert_not_awaited()
    error_response.body.get_reader().cancel.assert_awaited_once()


class _MockJsonResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        status: int = 200,
    ) -> None:
        self.ok = 200 <= status < 300
        self.status = status
        self._payload = payload

    async def json(self) -> Any:
        return self._payload
