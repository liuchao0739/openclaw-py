"""Tests for Codex media understanding provider."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openclaw_extensions.codex.media_understanding_provider import (
    build_codex_media_understanding_provider,
)


def _codex_model(input_modalities: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": "gpt-5.4",
        "model": "gpt-5.4",
        "displayName": "gpt-5.4",
        "hidden": False,
        "inputModalities": input_modalities or ["text", "image"],
        "supportedReasoningEfforts": ["low"],
        "isDefault": True,
    }


def _thread_start_result() -> dict[str, Any]:
    return {
        "thread": {
            "id": "thread-1",
            "status": {"type": "idle"},
        }
    }


def _turn_start_result(status: str = "inProgress") -> dict[str, Any]:
    return {"turn": {"id": "turn-1", "status": status, "items": []}}


def _create_fake_client() -> tuple[Any, list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []

    async def request(method: str, params: Any = None, **_kwargs: Any) -> Any:
        requests.append({"method": method, "params": params})
        if method == "model/list":
            return {"data": [_codex_model()]}
        if method == "thread/start":
            return _thread_start_result()
        if method == "turn/start":
            result = _turn_start_result()
            for handler in notification_handlers:
                handler(
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "item": {
                                "id": "assistant-1",
                                "type": "agentMessage",
                                "text": "A red square.",
                            },
                        },
                    }
                )
                handler(
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "turn": {"id": "turn-1", "status": "completed", "items": []},
                        },
                    }
                )
            return result
        return {}

    notification_handlers: list[Any] = []

    def add_notification_handler(handler: Any) -> Any:
        notification_handlers.append(handler)
        return lambda: notification_handlers.remove(handler)

    def add_request_handler(_handler: Any) -> Any:
        return lambda: None

    client = AsyncMock()
    client.request = request
    client.add_notification_handler = add_notification_handler
    client.add_request_handler = add_request_handler
    client.close = lambda: None
    return client, requests


@pytest.mark.asyncio
async def test_runs_image_understanding_through_a_bounded_codex_app_server_turn() -> None:
    client, requests = _create_fake_client()
    client_factory = AsyncMock(return_value=client)
    provider = build_codex_media_understanding_provider({"clientFactory": client_factory})
    cfg = {"auth": {"order": {"openai": ["openai:work"]}}}

    result = await provider["describeImage"](
        {
            "buffer": b"image-bytes",
            "fileName": "image.png",
            "mime": "image/png",
            "provider": "codex",
            "model": "gpt-5.4",
            "prompt": "Describe briefly.",
            "timeoutMs": 30_000,
            "cfg": cfg,
            "agentDir": "/tmp/openclaw-agent",
        }
    )

    assert result == {"text": "A red square.", "model": "gpt-5.4"}
    assert [entry["method"] for entry in requests] == ["model/list", "thread/start", "turn/start"]
    client_factory.assert_awaited_once()
    assert requests[1]["params"]["model"] == "gpt-5.4"
    assert requests[2]["params"]["input"] == [
        {"type": "text", "text": "Describe briefly.", "text_elements": []},
        {
            "type": "image",
            "url": f"data:image/png;base64,{base64.b64encode(b'image-bytes').decode('ascii')}",
        },
    ]
