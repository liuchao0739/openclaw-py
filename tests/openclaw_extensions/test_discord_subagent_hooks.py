"""Tests for Discord subagent hook handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from openclaw_extensions.discord.src.subagent_hooks import handle_discord_subagent_spawning
from openclaw_extensions.discord.subagent_hooks_api import register_discord_subagent_hooks


def _register_handlers_for_test(
    config: dict[str, Any] | None = None,
) -> dict[str, Callable[..., Any]]:
    handlers: dict[str, Callable[..., Any]] = {}

    class TestApi:
        def __init__(self, cfg: dict[str, Any]) -> None:
            self.config = cfg

        def on(self, hook_name: str, handler: Callable[..., Any]) -> None:
            handlers[hook_name] = handler

    api = TestApi(
        config
        or {
            "channels": {
                "discord": {
                    "threadBindings": {
                        "spawnSessions": True,
                    }
                }
            }
        }
    )
    register_discord_subagent_hooks(api)

    async def spawn_handler(event: dict[str, Any], _ctx: dict[str, Any] | None = None) -> Any:
        return await handle_discord_subagent_spawning(api, event)

    handlers["subagent_spawning"] = spawn_handler
    return handlers


def _create_spawn_event(**overrides: Any) -> dict[str, Any]:
    base = {
        "childSessionKey": "agent:main:subagent:child",
        "agentId": "main",
        "label": "banana",
        "mode": "session",
        "requester": {
            "channel": "discord",
            "accountId": "work",
            "to": "channel:123",
            "threadId": "456",
        },
        "threadRequested": True,
    }
    event = {**base, **overrides}
    if "requester" in overrides:
        event["requester"] = {**base["requester"], **overrides["requester"]}
    return event


class _ResolvedAccount:
    def __init__(self, account_id: str) -> None:
        self.account_id = account_id


@pytest.mark.asyncio
async def test_binds_thread_routing_on_subagent_spawning() -> None:
    auto_bind = AsyncMock(
        return_value=type("Binding", (), {"thread_id": "thread-1"})(),
    )

    def resolve_account(*, cfg: dict[str, Any], account_id: str | None = None) -> _ResolvedAccount:
        return _ResolvedAccount(account_id or "work")

    handlers = _register_handlers_for_test()
    with (
        patch(
            "openclaw_extensions.discord.src.subagent_hooks.resolve_discord_account",
            side_effect=resolve_account,
        ),
        patch(
            "openclaw_extensions.discord.src.subagent_hooks.auto_bind_spawned_discord_subagent",
            auto_bind,
        ),
    ):
        result = await handlers["subagent_spawning"](_create_spawn_event(), {})
    auto_bind.assert_awaited_once()
    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "deliveryOrigin": {
            "channel": "discord",
            "accountId": "work",
            "to": "channel:thread-1",
            "threadId": "thread-1",
        },
    }


@pytest.mark.asyncio
async def test_returns_error_when_thread_bound_subagent_spawn_is_disabled() -> None:
    handlers = _register_handlers_for_test(
        {
            "channels": {
                "discord": {
                    "threadBindings": {
                        "spawnSessions": False,
                    }
                }
            }
        }
    )
    with patch(
        "openclaw_extensions.discord.src.subagent_hooks.resolve_discord_account",
        return_value=_ResolvedAccount("work"),
    ):
        result = await handlers["subagent_spawning"](_create_spawn_event(), {})
    assert result["status"] == "error"
    assert "spawnSessions=true" in str(result["error"])


@pytest.mark.asyncio
async def test_unbinds_thread_routing_on_subagent_ended() -> None:
    unbind = Mock(return_value=[])
    handlers = _register_handlers_for_test()
    with patch(
        "openclaw_extensions.discord.src.subagent_hooks.unbind_thread_bindings_by_session_key",
        unbind,
    ):
        await handlers["subagent_ended"](
            {
                "targetSessionKey": "agent:main:subagent:child",
                "targetKind": "subagent",
                "reason": "subagent-complete",
                "sendFarewell": True,
                "accountId": "work",
            },
            {},
        )
    unbind.assert_called_once()


@pytest.mark.asyncio
async def test_resolves_delivery_target_from_matching_bound_thread() -> None:
    class Binding:
        account_id = "work"
        thread_id = "777"

    handlers = _register_handlers_for_test()
    with patch(
        "openclaw_extensions.discord.src.subagent_hooks.list_thread_bindings_by_session_key",
        return_value=[Binding()],
    ):
        result = await handlers["subagent_delivery_target"](
            {
                "childSessionKey": "agent:main:subagent:child",
                "requesterSessionKey": "agent:main:main",
                "requesterOrigin": {
                    "channel": "discord",
                    "accountId": "work",
                    "to": "channel:123",
                    "threadId": "777",
                },
                "expectsCompletionMessage": True,
            },
            {},
        )
    assert result == {
        "origin": {
            "channel": "discord",
            "accountId": "work",
            "to": "channel:777",
            "threadId": "777",
        }
    }
