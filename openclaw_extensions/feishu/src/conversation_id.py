"""Feishu plugin module implements conversation id behavior."""

from __future__ import annotations

import re
from typing import Literal

from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

FeishuGroupSessionScope = Literal[
    "group",
    "group_sender",
    "group_topic",
    "group_topic_sender",
]


def _normalize_text(value: object) -> str | None:
    return normalize_optional_string(value)


def build_feishu_conversation_id(
    *,
    chat_id: str,
    scope: FeishuGroupSessionScope,
    sender_open_id: str | None = None,
    topic_id: str | None = None,
) -> str:
    chat = _normalize_text(chat_id) or "unknown"
    sender_open_id_value = _normalize_text(sender_open_id)
    topic_id_value = _normalize_text(topic_id)

    if scope == "group_sender":
        return f"{chat}:sender:{sender_open_id_value}" if sender_open_id_value else chat
    if scope == "group_topic":
        return f"{chat}:topic:{topic_id_value}" if topic_id_value else chat
    if scope == "group_topic_sender":
        if topic_id_value and sender_open_id_value:
            return f"{chat}:topic:{topic_id_value}:sender:{sender_open_id_value}"
        if topic_id_value:
            return f"{chat}:topic:{topic_id_value}"
        if sender_open_id_value:
            return f"{chat}:sender:{sender_open_id_value}"
        return chat
    return chat


def parse_feishu_target_id(raw: object) -> str | None:
    target = _normalize_text(raw)
    if not target:
        return None
    without_provider = re.sub(r"^(feishu|lark):", "", target, flags=re.IGNORECASE).strip()
    if not without_provider:
        return None
    lowered = normalize_lowercase_string_or_empty(without_provider)
    for prefix in ("chat:", "group:", "channel:", "user:", "dm:", "open_id:"):
        if lowered.startswith(prefix):
            return _normalize_text(without_provider[len(prefix) :])
    return without_provider


def parse_feishu_direct_conversation_id(raw: object) -> str | None:
    target = _normalize_text(raw)
    if not target:
        return None
    without_provider = re.sub(r"^(feishu|lark):", "", target, flags=re.IGNORECASE).strip()
    if not without_provider:
        return None
    lowered = normalize_lowercase_string_or_empty(without_provider)
    for prefix in ("user:", "dm:", "open_id:"):
        if lowered.startswith(prefix):
            return _normalize_text(without_provider[len(prefix) :])
    parsed_id = parse_feishu_target_id(target)
    if not parsed_id:
        return None
    if parsed_id.startswith(("ou_", "on_")):
        return parsed_id
    return None


def parse_feishu_conversation_id(
    *,
    conversation_id: str,
    parent_conversation_id: str | None = None,
) -> dict[str, str] | None:
    conversation = _normalize_text(conversation_id)
    parent = _normalize_text(parent_conversation_id)
    if not conversation:
        return None

    topic_sender_match = re.match(
        r"^(.+):topic:([^:]+):sender:([^:]+)$",
        conversation,
        flags=re.IGNORECASE,
    )
    if topic_sender_match:
        chat_id, topic_id, sender_open_id = topic_sender_match.groups()
        return {
            "canonicalConversationId": build_feishu_conversation_id(
                chat_id=chat_id,
                scope="group_topic_sender",
                topic_id=topic_id,
                sender_open_id=sender_open_id,
            ),
            "chatId": chat_id,
            "topicId": topic_id,
            "senderOpenId": sender_open_id,
            "scope": "group_topic_sender",
        }

    topic_match = re.match(r"^(.+):topic:([^:]+)$", conversation, flags=re.IGNORECASE)
    if topic_match:
        chat_id, topic_id = topic_match.groups()
        return {
            "canonicalConversationId": build_feishu_conversation_id(
                chat_id=chat_id,
                scope="group_topic",
                topic_id=topic_id,
            ),
            "chatId": chat_id,
            "topicId": topic_id,
            "scope": "group_topic",
        }

    sender_match = re.match(r"^(.+):sender:([^:]+)$", conversation, flags=re.IGNORECASE)
    if sender_match:
        chat_id, sender_open_id = sender_match.groups()
        return {
            "canonicalConversationId": build_feishu_conversation_id(
                chat_id=chat_id,
                scope="group_sender",
                sender_open_id=sender_open_id,
            ),
            "chatId": chat_id,
            "senderOpenId": sender_open_id,
            "scope": "group_sender",
        }

    if parent:
        return {
            "canonicalConversationId": build_feishu_conversation_id(
                chat_id=parent,
                scope="group_topic",
                topic_id=conversation,
            ),
            "chatId": parent,
            "topicId": conversation,
            "scope": "group_topic",
        }

    return {
        "canonicalConversationId": conversation,
        "chatId": conversation,
        "scope": "group",
    }


def build_feishu_model_override_parent_candidates(
    parent_conversation_id: str | None = None,
) -> list[str]:
    raw_id = _normalize_text(parent_conversation_id)
    if not raw_id:
        return []

    topic_sender_match = re.match(
        r"^(.+):topic:([^:]+):sender:([^:]+)$",
        raw_id,
        flags=re.IGNORECASE,
    )
    if topic_sender_match:
        chat_id = normalize_lowercase_string_or_empty(topic_sender_match.group(1))
        topic_id = normalize_lowercase_string_or_empty(topic_sender_match.group(2))
        if chat_id and topic_id:
            return [f"{chat_id}:topic:{topic_id}", chat_id]
        return []

    topic_match = re.match(r"^(.+):topic:([^:]+)$", raw_id, flags=re.IGNORECASE)
    if topic_match:
        chat_id = normalize_lowercase_string_or_empty(topic_match.group(1))
        return [chat_id] if chat_id else []

    sender_match = re.match(r"^(.+):sender:([^:]+)$", raw_id, flags=re.IGNORECASE)
    if sender_match:
        chat_id = normalize_lowercase_string_or_empty(sender_match.group(1))
        return [chat_id] if chat_id else []

    return []


__all__ = [
    "FeishuGroupSessionScope",
    "build_feishu_conversation_id",
    "build_feishu_model_override_parent_candidates",
    "parse_feishu_conversation_id",
    "parse_feishu_direct_conversation_id",
    "parse_feishu_target_id",
]
