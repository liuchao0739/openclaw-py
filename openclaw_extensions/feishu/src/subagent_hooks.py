"""Feishu plugin module implements subagent hooks behavior."""

from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw_extensions.feishu.src.conversation_id import (
    build_feishu_conversation_id,
    parse_feishu_conversation_id,
)
from openclaw_extensions.feishu.src.targets import normalize_feishu_target
from openclaw_extensions.feishu.src.thread_bindings import (
    FeishuThreadBindingRecord,
    get_feishu_thread_binding_manager,
)


def _summarize_error(err: object) -> str:
    if isinstance(err, BaseException):
        return str(err)
    if isinstance(err, str):
        return err
    return "error"


def _strip_provider_prefix(raw: str) -> str:
    return re.sub(r"^(feishu|lark):", "", raw, flags=re.IGNORECASE).strip()


def _resolve_feishu_requester_conversation(
    *,
    account_id: str | None = None,
    to: str | None = None,
    thread_id: str | int | None = None,
    requester_session_key: str | None = None,
) -> dict[str, str] | None:
    manager = get_feishu_thread_binding_manager(account_id)
    if manager is None:
        return None

    raw_to = normalize_optional_string(to)
    without_provider_prefix = _strip_provider_prefix(raw_to) if raw_to else ""
    normalized_target = normalize_feishu_target(raw_to) if raw_to else None
    thread = (
        str(thread_id).strip()
        if thread_id is not None and str(thread_id).strip() != ""
        else ""
    )
    is_chat_target = bool(re.match(r"^(chat|group|channel):", without_provider_prefix, re.IGNORECASE))
    parsed_requester_topic = None
    if normalized_target and thread and is_chat_target:
        parsed_requester_topic = parse_feishu_conversation_id(
            conversation_id=build_feishu_conversation_id(
                chat_id=normalized_target,
                scope="group_topic",
                topic_id=thread,
            ),
            parent_conversation_id=normalized_target,
        )

    requester_key = normalize_optional_string(requester_session_key)
    if requester_key:
        existing_bindings = manager.list_by_session_key(requester_key)
        if len(existing_bindings) == 1:
            existing = existing_bindings[0]
            result = {
                "accountId": existing.account_id,
                "conversationId": existing.conversation_id,
            }
            if existing.parent_conversation_id:
                result["parentConversationId"] = existing.parent_conversation_id
            return result
        if len(existing_bindings) > 1:
            if raw_to and normalized_target and not thread and not is_chat_target:
                direct_matches = [
                    entry
                    for entry in existing_bindings
                    if entry.account_id == manager.account_id
                    and entry.conversation_id == normalized_target
                    and not entry.parent_conversation_id
                ]
                if len(direct_matches) == 1:
                    existing = direct_matches[0]
                    result = {
                        "accountId": existing.account_id,
                        "conversationId": existing.conversation_id,
                    }
                    if existing.parent_conversation_id:
                        result["parentConversationId"] = existing.parent_conversation_id
                    return result
                return None
            if parsed_requester_topic:
                matching_topic_bindings = [
                    entry
                    for entry in existing_bindings
                    if _topic_binding_matches(entry, parsed_requester_topic)
                ]
                if len(matching_topic_bindings) == 1:
                    existing = matching_topic_bindings[0]
                    result = {
                        "accountId": existing.account_id,
                        "conversationId": existing.conversation_id,
                    }
                    if existing.parent_conversation_id:
                        result["parentConversationId"] = existing.parent_conversation_id
                    return result
                sender_scoped_topic_bindings = [
                    entry
                    for entry in matching_topic_bindings
                    if _parsed_scope(entry) == "group_topic_sender"
                ]
                if (
                    len(sender_scoped_topic_bindings) == 1
                    and len(matching_topic_bindings) == len(sender_scoped_topic_bindings)
                ):
                    existing = sender_scoped_topic_bindings[0]
                    result = {
                        "accountId": existing.account_id,
                        "conversationId": existing.conversation_id,
                    }
                    if existing.parent_conversation_id:
                        result["parentConversationId"] = existing.parent_conversation_id
                    return result
                return None

    if not raw_to or not normalized_target:
        return None

    if thread:
        if not is_chat_target:
            return None
        return {
            "accountId": manager.account_id,
            "conversationId": build_feishu_conversation_id(
                chat_id=normalized_target,
                scope="group_topic",
                topic_id=thread,
            ),
            "parentConversationId": normalized_target,
        }

    if is_chat_target:
        return None

    return {
        "accountId": manager.account_id,
        "conversationId": normalized_target,
    }


def _parsed_scope(entry: FeishuThreadBindingRecord) -> str | None:
    parsed = parse_feishu_conversation_id(
        conversation_id=entry.conversation_id,
        parent_conversation_id=entry.parent_conversation_id,
    )
    return parsed.get("scope") if parsed else None


def _topic_binding_matches(
    entry: FeishuThreadBindingRecord,
    parsed_requester_topic: dict[str, str],
) -> bool:
    parsed = parse_feishu_conversation_id(
        conversation_id=entry.conversation_id,
        parent_conversation_id=entry.parent_conversation_id,
    )
    if not parsed:
        return False
    return (
        parsed.get("chatId") == parsed_requester_topic.get("chatId")
        and parsed.get("topicId") == parsed_requester_topic.get("topicId")
    )


def _resolve_feishu_delivery_origin(
    *,
    conversation_id: str,
    parent_conversation_id: str | None = None,
    account_id: str,
    delivery_to: str | None = None,
    delivery_thread_id: str | None = None,
) -> dict[str, Any]:
    delivery = normalize_optional_string(delivery_to)
    delivery_thread = normalize_optional_string(delivery_thread_id)
    if delivery:
        origin: dict[str, Any] = {
            "channel": "feishu",
            "accountId": account_id,
            "to": delivery,
        }
        if delivery_thread:
            origin["threadId"] = delivery_thread
        return origin

    parsed = parse_feishu_conversation_id(
        conversation_id=conversation_id,
        parent_conversation_id=parent_conversation_id,
    )
    if parsed and parsed.get("topicId"):
        parent = normalize_optional_string(parent_conversation_id) or parsed.get("chatId")
        origin = {
            "channel": "feishu",
            "accountId": account_id,
            "to": f"chat:{parent}",
            "threadId": parsed["topicId"],
        }
        return origin

    return {
        "channel": "feishu",
        "accountId": account_id,
        "to": f"user:{conversation_id}",
    }


def _resolve_matching_child_binding(
    *,
    account_id: str | None = None,
    child_session_key: str,
    requester_session_key: str | None = None,
    requester_origin: dict[str, Any] | None = None,
) -> FeishuThreadBindingRecord | None:
    manager = get_feishu_thread_binding_manager(account_id)
    if manager is None:
        return None

    child_bindings = manager.list_by_session_key(child_session_key.strip())
    if not child_bindings:
        return None

    requester_origin = requester_origin or {}
    requester_conversation = _resolve_feishu_requester_conversation(
        account_id=manager.account_id,
        to=requester_origin.get("to"),
        thread_id=requester_origin.get("threadId"),
        requester_session_key=requester_session_key,
    )
    if requester_conversation:
        for entry in child_bindings:
            if (
                entry.account_id == requester_conversation["accountId"]
                and entry.conversation_id == requester_conversation["conversationId"]
                and normalize_optional_string(entry.parent_conversation_id)
                == normalize_optional_string(requester_conversation.get("parentConversationId"))
            ):
                return entry

    return child_bindings[0] if len(child_bindings) == 1 else None


async def handle_feishu_subagent_spawning(
    event: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not event.get("threadRequested"):
        return None

    requester = event.get("requester") or {}
    requester_channel = normalize_optional_lowercase_string(requester.get("channel"))
    if requester_channel != "feishu":
        return None

    manager = get_feishu_thread_binding_manager(requester.get("accountId"))
    if manager is None:
        return {
            "status": "error",
            "error": (
                "Feishu current-conversation binding is unavailable because the Feishu "
                "account monitor is not active."
            ),
        }

    ctx = ctx or {}
    conversation = _resolve_feishu_requester_conversation(
        account_id=requester.get("accountId"),
        to=requester.get("to"),
        thread_id=requester.get("threadId"),
        requester_session_key=ctx.get("requesterSessionKey"),
    )
    if conversation is None:
        return {
            "status": "error",
            "error": (
                "Feishu current-conversation binding is only available in direct messages "
                "or topic conversations."
            ),
        }

    try:
        delivery_thread_id = requester.get("threadId")
        binding = manager.bind_conversation(
            conversation_id=conversation["conversationId"],
            parent_conversation_id=conversation.get("parentConversationId") or None,
            target_kind="subagent",
            target_session_key=event["childSessionKey"],
            metadata={
                "agentId": event.get("agentId"),
                "label": event.get("label"),
                "boundBy": "system",
                "deliveryTo": requester.get("to"),
                "deliveryThreadId": (
                    str(delivery_thread_id)
                    if delivery_thread_id is not None and str(delivery_thread_id) != ""
                    else None
                ),
            },
        )
        if binding is None:
            return {
                "status": "error",
                "error": (
                    "Unable to bind this Feishu conversation to the spawned subagent session. "
                    "Session mode is unavailable for this target."
                ),
            }
        return {
            "status": "ok",
            "threadBindingReady": True,
            "deliveryOrigin": _resolve_feishu_delivery_origin(
                conversation_id=binding.conversation_id,
                parent_conversation_id=binding.parent_conversation_id,
                account_id=binding.account_id,
                delivery_to=binding.delivery_to,
                delivery_thread_id=binding.delivery_thread_id,
            ),
        }
    except Exception as err:  # noqa: BLE001
        return {
            "status": "error",
            "error": f"Feishu conversation bind failed: {_summarize_error(err)}",
        }


def handle_feishu_subagent_delivery_target(event: dict[str, Any]) -> dict[str, Any] | None:
    if not event.get("expectsCompletionMessage"):
        return None

    requester_origin = event.get("requesterOrigin") or {}
    requester_channel = normalize_optional_lowercase_string(requester_origin.get("channel"))
    if requester_channel != "feishu":
        return None

    binding = _resolve_matching_child_binding(
        account_id=requester_origin.get("accountId"),
        child_session_key=event["childSessionKey"],
        requester_session_key=event.get("requesterSessionKey"),
        requester_origin={
            "to": requester_origin.get("to"),
            "threadId": requester_origin.get("threadId"),
        },
    )
    if binding is None:
        return None

    return {
        "origin": _resolve_feishu_delivery_origin(
            conversation_id=binding.conversation_id,
            parent_conversation_id=binding.parent_conversation_id,
            account_id=binding.account_id,
            delivery_to=binding.delivery_to,
            delivery_thread_id=binding.delivery_thread_id,
        )
    }


def handle_feishu_subagent_ended(event: dict[str, Any]) -> None:
    manager = get_feishu_thread_binding_manager(event.get("accountId"))
    if manager is not None:
        manager.unbind_by_session_key(event["targetSessionKey"])


__all__ = [
    "handle_feishu_subagent_delivery_target",
    "handle_feishu_subagent_ended",
    "handle_feishu_subagent_spawning",
]
