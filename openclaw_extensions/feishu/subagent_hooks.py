import re
from typing import Any, Optional

from .conversation_id import build_feishu_conversation_id, parse_feishu_conversation_id
from .targets import normalize_feishu_target
from .thread_bindings import get_feishu_thread_binding_manager


def _summarize_error(err: Any) -> str:
    if isinstance(err, Exception):
        return str(err.args[0] if err.args else err)
    if isinstance(err, str):
        return err
    return "error"


def _strip_provider_prefix(raw: str) -> str:
    return re.sub(r"^(feishu|lark):", "", raw, flags=re.IGNORECASE).strip()


def _normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_optional_lowercase(value: Any) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    return normalized.lower() if normalized else None


def resolve_feishu_requester_conversation(params: dict) -> Optional[dict]:
    manager = get_feishu_thread_binding_manager(params.get("accountId"))
    if not manager:
        return None
    raw_to = (params.get("to") or "").strip() if isinstance(params.get("to"), str) else ""
    without_provider_prefix = _strip_provider_prefix(raw_to) if raw_to else ""
    normalized_target = normalize_feishu_target(raw_to) if raw_to else None
    thread_id_raw = params.get("threadId")
    thread_id = str(thread_id_raw).strip() if thread_id_raw is not None and thread_id_raw != "" else ""
    is_chat_target = bool(re.match(r"^(chat|group|channel):", without_provider_prefix, re.IGNORECASE))

    parsed_requester_topic = None
    if normalized_target and thread_id and is_chat_target:
        parsed_requester_topic = parse_feishu_conversation_id({
            "conversationId": build_feishu_conversation_id({
                "chatId": normalized_target,
                "scope": "group_topic",
                "topicId": thread_id,
            }),
            "parentConversationId": normalized_target,
        })

    requester_session_key = (params.get("requesterSessionKey") or "").strip() if isinstance(params.get("requesterSessionKey"), str) else ""
    if requester_session_key:
        existing_bindings = manager["listBySessionKey"](requester_session_key)
        if len(existing_bindings) == 1:
            existing = existing_bindings[0]
            return {
                "accountId": existing["accountId"],
                "conversationId": existing["conversationId"],
                "parentConversationId": existing.get("parentConversationId"),
            }
        if len(existing_bindings) > 1:
            if raw_to and normalized_target and not thread_id and not is_chat_target:
                direct_matches = [
                    entry for entry in existing_bindings
                    if entry["accountId"] == manager["accountId"]
                    and entry["conversationId"] == normalized_target
                    and not entry.get("parentConversationId")
                ]
                if len(direct_matches) == 1:
                    existing = direct_matches[0]
                    return {
                        "accountId": existing["accountId"],
                        "conversationId": existing["conversationId"],
                        "parentConversationId": existing.get("parentConversationId"),
                    }
                return None
            if parsed_requester_topic:
                matching_topic_bindings = []
                for entry in existing_bindings:
                    parsed = parse_feishu_conversation_id({
                        "conversationId": entry["conversationId"],
                        "parentConversationId": entry.get("parentConversationId"),
                    })
                    if parsed and parsed.get("chatId") == parsed_requester_topic.get("chatId") and parsed.get("topicId") == parsed_requester_topic.get("topicId"):
                        matching_topic_bindings.append(entry)
                if len(matching_topic_bindings) == 1:
                    existing = matching_topic_bindings[0]
                    return {
                        "accountId": existing["accountId"],
                        "conversationId": existing["conversationId"],
                        "parentConversationId": existing.get("parentConversationId"),
                    }
                sender_scoped_topic_bindings = [
                    entry for entry in matching_topic_bindings
                    if parse_feishu_conversation_id({
                        "conversationId": entry["conversationId"],
                        "parentConversationId": entry.get("parentConversationId"),
                    }).get("scope") == "group_topic_sender"
                ]
                if (
                    len(sender_scoped_topic_bindings) == 1
                    and len(matching_topic_bindings) == len(sender_scoped_topic_bindings)
                ):
                    existing = sender_scoped_topic_bindings[0]
                    return {
                        "accountId": existing["accountId"],
                        "conversationId": existing["conversationId"],
                        "parentConversationId": existing.get("parentConversationId"),
                    }
                return None
            return None

    if not raw_to:
        return None
    if not normalized_target:
        return None

    if thread_id:
        if not is_chat_target:
            return None
        return {
            "accountId": manager["accountId"],
            "conversationId": build_feishu_conversation_id({
                "chatId": normalized_target,
                "scope": "group_topic",
                "topicId": thread_id,
            }),
            "parentConversationId": normalized_target,
        }

    if is_chat_target:
        return None

    return {
        "accountId": manager["accountId"],
        "conversationId": normalized_target,
    }


def resolve_feishu_delivery_origin(params: dict) -> dict:
    delivery_to = (params.get("deliveryTo") or "").strip() if isinstance(params.get("deliveryTo"), str) else ""
    delivery_thread_id = (params.get("deliveryThreadId") or "").strip() if isinstance(params.get("deliveryThreadId"), str) else ""
    if delivery_to:
        result = {
            "channel": "feishu",
            "accountId": params.get("accountId", ""),
            "to": delivery_to,
        }
        if delivery_thread_id:
            result["threadId"] = delivery_thread_id
        return result
    parsed = parse_feishu_conversation_id({
        "conversationId": params.get("conversationId", ""),
        "parentConversationId": params.get("parentConversationId"),
    })
    if parsed and parsed.get("topicId"):
        parent = (params.get("parentConversationId") or "").strip() if isinstance(params.get("parentConversationId"), str) else ""
        return {
            "channel": "feishu",
            "accountId": params.get("accountId", ""),
            "to": f"chat:{parent or parsed.get('chatId', '')}",
            "threadId": parsed.get("topicId"),
        }
    return {
        "channel": "feishu",
        "accountId": params.get("accountId", ""),
        "to": f"user:{params.get('conversationId', '')}",
    }


def resolve_matching_child_binding(params: dict) -> Optional[dict]:
    manager = get_feishu_thread_binding_manager(params.get("accountId"))
    if not manager:
        return None
    child_session_key = (params.get("childSessionKey") or "").strip()
    child_bindings = manager["listBySessionKey"](child_session_key)
    if not child_bindings:
        return None

    requester_origin = params.get("requesterOrigin") or {}
    requester_conversation = resolve_feishu_requester_conversation({
        "accountId": manager["accountId"],
        "to": requester_origin.get("to"),
        "threadId": requester_origin.get("threadId"),
        "requesterSessionKey": params.get("requesterSessionKey"),
    })
    if requester_conversation:
        for entry in child_bindings:
            if (
                entry["accountId"] == requester_conversation["accountId"]
                and entry["conversationId"] == requester_conversation["conversationId"]
                and _normalize_optional_string(entry.get("parentConversationId")) == _normalize_optional_string(requester_conversation.get("parentConversationId"))
            ):
                return entry
    return child_bindings[0] if len(child_bindings) == 1 else None


async def handle_feishu_subagent_spawning(event: dict, ctx: dict) -> Optional[dict]:
    if not event.get("threadRequested"):
        return None
    requester = event.get("requester") or {}
    if _normalize_optional_lowercase(requester.get("channel")) != "feishu":
        return None

    manager = get_feishu_thread_binding_manager(requester.get("accountId"))
    if not manager:
        return {
            "status": "error",
            "error": "Feishu current-conversation binding is unavailable because the Feishu account monitor is not active.",
        }

    conversation = resolve_feishu_requester_conversation({
        "accountId": requester.get("accountId"),
        "to": requester.get("to"),
        "threadId": requester.get("threadId"),
        "requesterSessionKey": ctx.get("requesterSessionKey"),
    })
    if not conversation:
        return {
            "status": "error",
            "error": "Feishu current-conversation binding is only available in direct messages or topic conversations.",
        }

    try:
        thread_id_raw = requester.get("threadId")
        delivery_thread_id = str(thread_id_raw) if thread_id_raw is not None and thread_id_raw != "" else None
        binding = manager["bindConversation"]({
            "conversationId": conversation["conversationId"],
            "parentConversationId": conversation.get("parentConversationId"),
            "targetKind": "subagent",
            "targetSessionKey": event.get("childSessionKey", ""),
            "metadata": {
                "agentId": event.get("agentId"),
                "label": event.get("label"),
                "boundBy": "system",
                "deliveryTo": requester.get("to"),
                "deliveryThreadId": delivery_thread_id,
            },
        })
        if not binding:
            return {
                "status": "error",
                "error": "Unable to bind this Feishu conversation to the spawned subagent session. Session mode is unavailable for this target.",
            }
        return {
            "status": "ok",
            "threadBindingReady": True,
            "deliveryOrigin": resolve_feishu_delivery_origin({
                "conversationId": binding["conversationId"],
                "parentConversationId": binding.get("parentConversationId"),
                "accountId": binding["accountId"],
                "deliveryTo": binding.get("deliveryTo"),
                "deliveryThreadId": binding.get("deliveryThreadId"),
            }),
        }
    except Exception as err:
        return {
            "status": "error",
            "error": f"Feishu conversation bind failed: {_summarize_error(err)}",
        }


def handle_feishu_subagent_delivery_target(event: dict) -> Optional[dict]:
    if not event.get("expectsCompletionMessage"):
        return None
    requester_origin = event.get("requesterOrigin") or {}
    if _normalize_optional_lowercase(requester_origin.get("channel")) != "feishu":
        return None

    binding = resolve_matching_child_binding({
        "accountId": requester_origin.get("accountId"),
        "childSessionKey": event.get("childSessionKey", ""),
        "requesterSessionKey": event.get("requesterSessionKey"),
        "requesterOrigin": {
            "to": requester_origin.get("to"),
            "threadId": requester_origin.get("threadId"),
        },
    })
    if not binding:
        return None

    return {
        "origin": resolve_feishu_delivery_origin({
            "conversationId": binding["conversationId"],
            "parentConversationId": binding.get("parentConversationId"),
            "accountId": binding["accountId"],
            "deliveryTo": binding.get("deliveryTo"),
            "deliveryThreadId": binding.get("deliveryThreadId"),
        })
    }


def handle_feishu_subagent_ended(event: dict) -> None:
    manager = get_feishu_thread_binding_manager(event.get("accountId"))
    if manager:
        manager["unbindBySessionKey"](event.get("targetSessionKey", ""))
