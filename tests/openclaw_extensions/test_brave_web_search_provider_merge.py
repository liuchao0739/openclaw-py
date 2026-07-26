"""Tests for brave web search config merge behavior."""

from __future__ import annotations

from typing import Any

import pytest

from openclaw_extensions.brave.src import brave_web_search_provider_runtime as runtime_module
from openclaw_extensions.brave.src.brave_web_search_provider import create_brave_web_search_provider


@pytest.mark.asyncio
async def test_keeps_plugin_web_search_runtime_only_after_merging_it_for_the_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any] | None] = []

    async def fake_execute_brave_search(
        _args: dict[str, Any],
        search_config: dict[str, Any] | None = None,
        _options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured.append(search_config)
        return {"results": []}

    monkeypatch.setattr(runtime_module, "execute_brave_search", fake_execute_brave_search)

    provider = create_brave_web_search_provider()
    tool = provider["create_tool"](
        {
            "config": {
                "plugins": {
                    "entries": {
                        "brave": {
                            "config": {
                                "webSearch": {
                                    "apiKey": "brave-test-key",
                                    "mode": "llm-context",
                                }
                            }
                        }
                    }
                }
            },
            "search_config": {"provider": "brave"},
        }
    )
    assert tool is not None

    await tool["execute"]({"query": "OpenClaw docs"})

    search_config = captured[0]
    assert search_config is not None
    assert search_config["brave"] == {
        "apiKey": "brave-test-key",
        "mode": "llm-context",
    }
    assert search_config["apiKey"] == "brave-test-key"
    assert set(search_config.keys()) == {"provider", "apiKey", "brave"}
