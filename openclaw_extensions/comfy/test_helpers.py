"""Test helpers for Comfy provider tests."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch


def build_comfy_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "plugins": {
            "entries": {
                "comfy": {"config": config},
            },
        },
    }


def build_legacy_comfy_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "models": {
            "providers": {
                "comfy": config,
            },
        },
    }


def parse_comfy_json_body(fetch_guard_mock: Any, call: int) -> dict[str, Any]:
    request = fetch_guard_mock.call_args_list[call - 1].args[0]
    body = (request.get("init") or {}).get("body")
    assert body
    if not isinstance(body, str):
        raise TypeError(f"Missing Comfy request body for fetch call {call}")
    return json.loads(body)


def mock_comfy_provider_api_key(api_key: str = "comfy-test-key") -> Any:
    mock = AsyncMock(
        return_value={
            "apiKey": api_key,
            "source": "env",
            "mode": "api-key",
        }
    )
    return patch(
        "openclaw_extensions.comfy.workflow_runtime.resolve_api_key_for_provider",
        mock,
    )


class _MockResponse:
    def __init__(
        self,
        *,
        content: bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
        ok: bool | None = None,
    ) -> None:
        self._content = content
        self.status = status
        self.ok = ok if ok is not None else 200 <= status < 300
        self.headers = headers or {}

    async def json(self) -> Any:
        return json.loads(self._content.decode("utf-8"))

    async def aread(self) -> bytes:
        return self._content


def _fetch_guard_json(body: Any) -> dict[str, Any]:
    return _fetch_guard_response(
        _MockResponse(
            content=json.dumps(body).encode("utf-8"),
            status=200,
            headers={"content-type": "application/json"},
        )
    )


def _fetch_guard_response(response: _MockResponse) -> dict[str, Any]:
    async def release() -> None:
        return None

    return {"response": response, "release": release}


def mock_comfy_cloud_job_responses(
    fetch_guard_mock: Any,
    *,
    body: bytes,
    content_type: str,
    filename: str,
    output_kind: str,
    prompt_id: str,
    redirect_location: str,
) -> None:
    fetch_guard_mock.side_effect = [
        _fetch_guard_json({"prompt_id": prompt_id}),
        _fetch_guard_json({"status": "completed"}),
        _fetch_guard_json(
            {
                prompt_id: {
                    "outputs": {
                        "9": {
                            output_kind: [
                                {"filename": filename, "subfolder": "", "type": "output"},
                            ],
                        },
                    },
                },
            }
        ),
        _fetch_guard_response(
            _MockResponse(
                content=b"",
                status=302,
                headers={"location": redirect_location},
            )
        ),
        _fetch_guard_response(
            _MockResponse(
                content=body,
                status=200,
                headers={"content-type": content_type},
            )
        ),
    ]
