"""Tests for Feishu subagent hook handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from openclaw_extensions.feishu.api import feishu_session_binding_adapter_channels
from openclaw_extensions.feishu.src.subagent_hooks import handle_feishu_subagent_spawning
from openclaw_extensions.feishu.src.thread_bindings import (
    create_feishu_thread_binding_manager,
)
from openclaw_extensions.feishu.src.thread_bindings import (
    testing as thread_binding_testing,
)
from openclaw_extensions.feishu.subagent_hooks_api import register_feishu_subagent_hooks

BASE_CONFIG: dict[str, Any] = {
    "session": {"mainKey": "main", "scope": "per-sender"},
    "channels": {"feishu": {}},
}


def _register_handlers_for_test(
    config: dict[str, Any] | None = None,
) -> dict[str, Callable[..., Any]]:
    handlers: dict[str, Callable[..., Any]] = {}

    class TestApi:
        def __init__(self, cfg: dict[str, Any]) -> None:
            self.config = cfg

        def on(self, hook_name: str, handler: Callable[..., Any]) -> None:
            handlers[hook_name] = handler

    api = TestApi(config or BASE_CONFIG)
    register_feishu_subagent_hooks(api)
    api.on(
        "subagent_spawning",
        lambda event, ctx: handle_feishu_subagent_spawning(event, ctx),
    )
    return handlers


def _get_required_hook_handler(
    handlers: dict[str, Callable[..., Any]],
    hook_name: str,
) -> Callable[..., Any]:
    handler = handlers.get(hook_name)
    if handler is None:
        raise AssertionError(f"expected {hook_name} hook handler")
    return handler


async def _expect_hook_error(value: Any, expected_error_fragment: str) -> None:
    result = await value
    assert result.get("status") == "error"
    assert expected_error_fragment in str(result.get("error"))


@pytest.fixture(autouse=True)
def _reset_thread_bindings() -> None:
    thread_binding_testing.reset_feishu_thread_bindings_for_tests()


def test_feishu_session_binding_adapter_channels() -> None:
    assert feishu_session_binding_adapter_channels == ("feishu",)


@pytest.mark.asyncio
async def test_binds_feishu_dm_conversation_on_subagent_spawning() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    result = await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:child",
            "agentId": "codex",
            "label": "banana",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "threadRequested": True,
        },
        {},
    )

    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "deliveryOrigin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "user:ou_sender_1",
        },
    }

    delivery_target_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    delivery_result = await delivery_target_handler(
        {
            "childSessionKey": "agent:main:subagent:child",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result == {
        "origin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "user:ou_sender_1",
        },
    }


@pytest.mark.asyncio
async def test_preserves_original_feishu_dm_delivery_target() -> None:
    handlers = _register_handlers_for_test()
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    manager = create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    manager.bind_conversation(
        conversation_id="ou_sender_1",
        target_kind="subagent",
        target_session_key="agent:main:subagent:chat-dm-child",
        metadata={
            "deliveryTo": "chat:oc_dm_chat_1",
            "boundBy": "system",
        },
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:chat-dm-child",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_dm_chat_1",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result == {
        "origin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "chat:oc_dm_chat_1",
        },
    }


@pytest.mark.asyncio
async def test_binds_feishu_topic_conversation_and_preserves_parent_context() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    result = await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:topic-child",
            "agentId": "codex",
            "label": "topic-child",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "threadRequested": True,
        },
        {},
    )

    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "deliveryOrigin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "chat:oc_group_chat",
            "threadId": "om_topic_root",
        },
    }

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:topic-child",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result == {
        "origin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "chat:oc_group_chat",
            "threadId": "om_topic_root",
        },
    }


@pytest.mark.asyncio
async def test_uses_requester_session_binding_for_sender_scoped_topic_conversations() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    manager = create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    manager.bind_conversation(
        conversation_id="oc_group_chat:topic:om_topic_root:sender:ou_sender_1",
        parent_conversation_id="oc_group_chat",
        target_kind="subagent",
        target_session_key="agent:main:parent",
        metadata={
            "agentId": "codex",
            "label": "parent",
            "boundBy": "system",
        },
    )

    rebound_result = await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:sender-child",
            "agentId": "codex",
            "label": "sender-child",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "threadRequested": True,
        },
        {"requesterSessionKey": "agent:main:parent"},
    )

    assert rebound_result == {
        "status": "ok",
        "threadBindingReady": True,
        "deliveryOrigin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "chat:oc_group_chat",
            "threadId": "om_topic_root",
        },
    }

    child_bindings = manager.list_by_session_key("agent:main:subagent:sender-child")
    assert len(child_bindings) == 1
    assert (
        child_bindings[0].conversation_id == "oc_group_chat:topic:om_topic_root:sender:ou_sender_1"
    )
    assert child_bindings[0].parent_conversation_id == "oc_group_chat"

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:sender-child",
            "requesterSessionKey": "agent:main:parent",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result == {
        "origin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "chat:oc_group_chat",
            "threadId": "om_topic_root",
        },
    }


@pytest.mark.asyncio
async def test_prefers_requester_matching_bindings_when_multiple_child_bindings_exist() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:shared",
            "agentId": "codex",
            "label": "shared",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "threadRequested": True,
        },
        {},
    )
    await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:shared",
            "agentId": "codex",
            "label": "shared",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_2",
            },
            "threadRequested": True,
        },
        {},
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:shared",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_2",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result == {
        "origin": {
            "channel": "feishu",
            "accountId": "work",
            "to": "user:ou_sender_2",
        },
    }


@pytest.mark.asyncio
async def test_fails_closed_when_requester_session_bindings_remain_ambiguous_for_same_topic() -> (
    None
):
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    manager = create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    manager.bind_conversation(
        conversation_id="oc_group_chat:topic:om_topic_root:sender:ou_sender_1",
        parent_conversation_id="oc_group_chat",
        target_kind="subagent",
        target_session_key="agent:main:parent",
        metadata={"boundBy": "system"},
    )
    manager.bind_conversation(
        conversation_id="oc_group_chat:topic:om_topic_root:sender:ou_sender_2",
        parent_conversation_id="oc_group_chat",
        target_kind="subagent",
        target_session_key="agent:main:parent",
        metadata={"boundBy": "system"},
    )

    await _expect_hook_error(
        spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:ambiguous-child",
                "agentId": "codex",
                "label": "ambiguous-child",
                "mode": "session",
                "requester": {
                    "channel": "feishu",
                    "accountId": "work",
                    "to": "chat:oc_group_chat",
                    "threadId": "om_topic_root",
                },
                "threadRequested": True,
            },
            {"requesterSessionKey": "agent:main:parent"},
        ),
        "direct messages or topic conversations",
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:ambiguous-child",
            "requesterSessionKey": "agent:main:parent",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result is None


@pytest.mark.asyncio
async def test_fails_closed_when_both_topic_level_and_sender_scoped_requester_bindings_exist() -> (
    None
):
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    manager = create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    manager.bind_conversation(
        conversation_id="oc_group_chat:topic:om_topic_root",
        parent_conversation_id="oc_group_chat",
        target_kind="subagent",
        target_session_key="agent:main:parent",
        metadata={"boundBy": "system"},
    )
    manager.bind_conversation(
        conversation_id="oc_group_chat:topic:om_topic_root:sender:ou_sender_1",
        parent_conversation_id="oc_group_chat",
        target_kind="subagent",
        target_session_key="agent:main:parent",
        metadata={"boundBy": "system"},
    )

    await _expect_hook_error(
        spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:mixed-topic-child",
                "agentId": "codex",
                "label": "mixed-topic-child",
                "mode": "session",
                "requester": {
                    "channel": "feishu",
                    "accountId": "work",
                    "to": "chat:oc_group_chat",
                    "threadId": "om_topic_root",
                },
                "threadRequested": True,
            },
            {"requesterSessionKey": "agent:main:parent"},
        ),
        "direct messages or topic conversations",
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:mixed-topic-child",
            "requesterSessionKey": "agent:main:parent",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "chat:oc_group_chat",
                "threadId": "om_topic_root",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result is None


@pytest.mark.asyncio
async def test_no_ops_for_non_feishu_channels_and_non_threaded_spawns() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    ended_handler = _get_required_hook_handler(handlers, "subagent_ended")

    assert (
        await spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:child",
                "agentId": "codex",
                "mode": "run",
                "requester": {
                    "channel": "discord",
                    "accountId": "work",
                    "to": "channel:123",
                },
                "threadRequested": True,
            },
            {},
        )
        is None
    )

    assert (
        await spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:child",
                "agentId": "codex",
                "mode": "run",
                "requester": {
                    "channel": "feishu",
                    "accountId": "work",
                    "to": "user:ou_sender_1",
                },
                "threadRequested": False,
            },
            {},
        )
        is None
    )

    assert (
        await delivery_handler(
            {
                "childSessionKey": "agent:main:subagent:child",
                "requesterSessionKey": "agent:main:main",
                "requesterOrigin": {
                    "channel": "discord",
                    "accountId": "work",
                    "to": "channel:123",
                },
                "expectsCompletionMessage": True,
            },
            {},
        )
        is None
    )

    assert (
        await ended_handler(
            {
                "targetSessionKey": "agent:main:subagent:child",
                "targetKind": "subagent",
                "reason": "done",
                "accountId": "work",
            },
            {},
        )
        is None
    )


@pytest.mark.asyncio
async def test_returns_error_for_unsupported_non_topic_feishu_group_conversations() -> None:
    spawn_handler = _get_required_hook_handler(_register_handlers_for_test(), "subagent_spawning")
    create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    await _expect_hook_error(
        spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:child",
                "agentId": "codex",
                "mode": "session",
                "requester": {
                    "channel": "feishu",
                    "accountId": "work",
                    "to": "chat:oc_group_chat",
                },
                "threadRequested": True,
            },
            {},
        ),
        "direct messages or topic conversations",
    )


@pytest.mark.asyncio
async def test_unbinds_feishu_bindings_on_subagent_ended() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")
    ended_handler = _get_required_hook_handler(handlers, "subagent_ended")
    create_feishu_thread_binding_manager(cfg=BASE_CONFIG, account_id="work")

    await spawn_handler(
        {
            "childSessionKey": "agent:main:subagent:child",
            "agentId": "codex",
            "mode": "session",
            "requester": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "threadRequested": True,
        },
        {},
    )

    await ended_handler(
        {
            "targetSessionKey": "agent:main:subagent:child",
            "targetKind": "subagent",
            "reason": "done",
            "accountId": "work",
        },
        {},
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:child",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result is None


@pytest.mark.asyncio
async def test_fails_closed_when_feishu_binding_manager_is_unavailable() -> None:
    handlers = _register_handlers_for_test()
    spawn_handler = _get_required_hook_handler(handlers, "subagent_spawning")
    delivery_handler = _get_required_hook_handler(handlers, "subagent_delivery_target")

    await _expect_hook_error(
        spawn_handler(
            {
                "childSessionKey": "agent:main:subagent:no-manager",
                "agentId": "codex",
                "mode": "session",
                "requester": {
                    "channel": "feishu",
                    "accountId": "work",
                    "to": "user:ou_sender_1",
                },
                "threadRequested": True,
            },
            {},
        ),
        "monitor is not active",
    )

    delivery_result = await delivery_handler(
        {
            "childSessionKey": "agent:main:subagent:no-manager",
            "requesterSessionKey": "agent:main:main",
            "requesterOrigin": {
                "channel": "feishu",
                "accountId": "work",
                "to": "user:ou_sender_1",
            },
            "expectsCompletionMessage": True,
        },
        {},
    )
    assert delivery_result is None
