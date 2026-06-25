"""Builds plugin hook context metadata for native agent harness events.

Only stable run/session/model facts are forwarded to plugin hooks; config remains a local
construction input so hooks do not accidentally depend on mutable raw configuration.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentHarnessHookContext(TypedDict, total=False):
    runId: str
    trace: Any
    jobId: str
    agentId: str
    sessionKey: str
    sessionId: str
    workspaceDir: str
    modelProviderId: str
    modelId: str
    messageProvider: str
    channel: str
    chatId: str
    senderId: str
    trigger: str
    channelId: str
    contextTokenBudget: int
    contextWindowSource: str
    contextWindowReferenceTokens: int
    config: Any


_OPTIONAL_FIELDS = (
    "trace",
    "jobId",
    "agentId",
    "sessionKey",
    "sessionId",
    "workspaceDir",
    "modelProviderId",
    "modelId",
    "messageProvider",
    "channel",
    "chatId",
    "senderId",
    "trigger",
    "channelId",
    "contextTokenBudget",
    "contextWindowSource",
    "contextWindowReferenceTokens",
    "config",
)


def build_agent_hook_context(params: AgentHarnessHookContext) -> dict[str, Any]:
    """Build the sparse hook context object passed to agent harness plugin hooks."""
    ctx: dict[str, Any] = {"runId": params["runId"]}
    for field in _OPTIONAL_FIELDS:
        value = params.get(field)  # type: ignore[call-overload]
        if value is not None:
            if field == "contextTokenBudget" and not value:
                continue
            ctx[field] = value
    return ctx
