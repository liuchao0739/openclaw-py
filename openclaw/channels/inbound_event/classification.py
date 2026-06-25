"""Channel inbound event classifier.

Decides whether group/channel activity should wake the agent or remain a passive room event.
"""

from __future__ import annotations

from typing import Any, Literal

InboundEventKind = Literal["user_request", "room_event"]


def classify_channel_inbound_event(
    conversation_kind: str | None = None,
    unmentioned_group_policy: InboundEventKind | None = None,
    was_mentioned: bool = False,
    has_control_command: bool = False,
    has_abort_request: bool = False,
    command_source: str | None = None,
) -> InboundEventKind:
    """Classify an inbound channel event as an actionable request or passive room event."""
    if unmentioned_group_policy != "room_event":
        return "user_request"
    if conversation_kind not in ("group", "channel"):
        return "user_request"
    if was_mentioned or has_control_command or has_abort_request or command_source == "native":
        return "user_request"
    return "room_event"


def resolve_unmentioned_group_inbound_policy(
    cfg: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> InboundEventKind:
    """Resolve the configured policy for unmentioned group/channel inbound events."""
    if not cfg:
        return "user_request"

    # Check agent-specific config first
    if agent_id:
        agents = cfg.get("agents", {})
        if isinstance(agents, dict):
            agent_list = agents.get("list", [])
            if isinstance(agent_list, list):
                for agent in agent_list:
                    if isinstance(agent, dict) and agent.get("id") == agent_id:
                        group_chat = agent.get("groupChat", {})
                        if isinstance(group_chat, dict) and "unmentionedInbound" in group_chat:
                            return group_chat["unmentionedInbound"]

    # Fall back to global config
    messages = cfg.get("messages", {})
    if isinstance(messages, dict):
        group_chat = messages.get("groupChat", {})
        if isinstance(group_chat, dict) and "unmentionedInbound" in group_chat:
            return group_chat["unmentionedInbound"]

    return "user_request"
