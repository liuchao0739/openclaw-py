import re
from typing import Optional, TypedDict, Literal

from .types import FeishuGroupSessionScope


def _normalize_text(value) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_lower(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def build_feishu_conversation_id(params: dict) -> str:
    chat_id = _normalize_text(params.get("chatId")) or "unknown"
    sender_open_id = _normalize_text(params.get("senderOpenId"))
    topic_id = _normalize_text(params.get("topicId"))
    scope = params.get("scope")

    if scope == "group_sender":
        return f"{chat_id}:sender:{sender_open_id}" if sender_open_id else chat_id
    if scope == "group_topic":
        return f"{chat_id}:topic:{topic_id}" if topic_id else chat_id
    if scope == "group_topic_sender":
        if topic_id and sender_open_id:
            return f"{chat_id}:topic:{topic_id}:sender:{sender_open_id}"
        if topic_id:
            return f"{chat_id}:topic:{topic_id}"
        return f"{chat_id}:sender:{sender_open_id}" if sender_open_id else chat_id
    return chat_id


def parse_feishu_target_id(raw) -> Optional[str]:
    target = _normalize_text(raw)
    if not target:
        return None
    without_provider = re.sub(r"^(feishu|lark):", "", target, flags=re.IGNORECASE).strip()
    if not without_provider:
        return None
    lowered = _normalize_lower(without_provider)
    for prefix in ["chat:", "group:", "channel:", "user:", "dm:", "open_id:"]:
        if lowered.startswith(prefix):
            return _normalize_text(without_provider[len(prefix):])
    return without_provider


def parse_feishu_direct_conversation_id(raw) -> Optional[str]:
    target = _normalize_text(raw)
    if not target:
        return None
    without_provider = re.sub(r"^(feishu|lark):", "", target, flags=re.IGNORECASE).strip()
    if not without_provider:
        return None
    lowered = _normalize_lower(without_provider)
    for prefix in ["user:", "dm:", "open_id:"]:
        if lowered.startswith(prefix):
            return _normalize_text(without_provider[len(prefix):])
    id_value = parse_feishu_target_id(target)
    if not id_value:
        return None
    if id_value.startswith("ou_") or id_value.startswith("on_"):
        return id_value
    return None


class ParsedFeishuConversationId(TypedDict, total=False):
    canonicalConversationId: str
    chatId: str
    topicId: Optional[str]
    senderOpenId: Optional[str]
    scope: FeishuGroupSessionScope


_TOPIC_SENDER_RE = re.compile(r"^(.+):topic:([^:]+):sender:([^:]+)$", re.IGNORECASE)
_TOPIC_RE = re.compile(r"^(.+):topic:([^:]+)$", re.IGNORECASE)
_SENDER_RE = re.compile(r"^(.+):sender:([^:]+)$", re.IGNORECASE)


def parse_feishu_conversation_id(params: dict) -> Optional[ParsedFeishuConversationId]:
    conversation_id = _normalize_text(params.get("conversationId"))
    parent_conversation_id = _normalize_text(params.get("parentConversationId"))
    if not conversation_id:
        return None

    topic_sender_match = _TOPIC_SENDER_RE.match(conversation_id)
    if topic_sender_match:
        chat_id, topic_id, sender_open_id = topic_sender_match.group(1), topic_sender_match.group(2), topic_sender_match.group(3)
        return {
            "canonicalConversationId": build_feishu_conversation_id({
                "chatId": chat_id,
                "scope": "group_topic_sender",
                "topicId": topic_id,
                "senderOpenId": sender_open_id,
            }),
            "chatId": chat_id,
            "topicId": topic_id,
            "senderOpenId": sender_open_id,
            "scope": "group_topic_sender",
        }

    topic_match = _TOPIC_RE.match(conversation_id)
    if topic_match:
        chat_id, topic_id = topic_match.group(1), topic_match.group(2)
        return {
            "canonicalConversationId": build_feishu_conversation_id({
                "chatId": chat_id,
                "scope": "group_topic",
                "topicId": topic_id,
            }),
            "chatId": chat_id,
            "topicId": topic_id,
            "scope": "group_topic",
        }

    sender_match = _SENDER_RE.match(conversation_id)
    if sender_match:
        chat_id, sender_open_id = sender_match.group(1), sender_match.group(2)
        return {
            "canonicalConversationId": build_feishu_conversation_id({
                "chatId": chat_id,
                "scope": "group_sender",
                "senderOpenId": sender_open_id,
            }),
            "chatId": chat_id,
            "senderOpenId": sender_open_id,
            "scope": "group_sender",
        }

    if parent_conversation_id:
        return {
            "canonicalConversationId": build_feishu_conversation_id({
                "chatId": parent_conversation_id,
                "scope": "group_topic",
                "topicId": conversation_id,
            }),
            "chatId": parent_conversation_id,
            "topicId": conversation_id,
            "scope": "group_topic",
        }

    return {
        "canonicalConversationId": conversation_id,
        "chatId": conversation_id,
        "scope": "group",
    }


def build_feishu_model_override_parent_candidates(parent_conversation_id=None) -> list:
    raw_id = _normalize_text(parent_conversation_id)
    if not raw_id:
        return []
    topic_sender_match = _TOPIC_SENDER_RE.match(raw_id)
    if topic_sender_match:
        chat_id = _normalize_lower(topic_sender_match.group(1))
        topic_id = _normalize_lower(topic_sender_match.group(2))
        if chat_id and topic_id:
            return [f"{chat_id}:topic:{topic_id}", chat_id]
        return []
    topic_match = _TOPIC_RE.match(raw_id)
    if topic_match:
        chat_id = _normalize_lower(topic_match.group(1))
        return [chat_id] if chat_id else []
    sender_match = _SENDER_RE.match(raw_id)
    if sender_match:
        chat_id = _normalize_lower(sender_match.group(1))
        return [chat_id] if chat_id else []
    return []
