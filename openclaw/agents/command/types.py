"""Agent command option types (partial port)."""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.agents.command.shared_types import AgentStreamParams


class AgentRunContext(TypedDict, total=False):
    messageChannel: str
    accountId: str
    groupId: str
    groupChannel: str
    groupSpace: str
    currentThreadTs: str
    currentChannelId: str


class AgentCommandOpts(TypedDict, total=False):
    runContext: AgentRunContext
    messageChannel: str
    replyChannel: str
    channel: str
    accountId: str
    groupId: str
    groupChannel: str
    groupSpace: str
    threadId: str | int
    to: str
    streamParams: AgentStreamParams
    sessionId: str
    sessionKey: str
    agentId: str
    config: dict[str, Any]