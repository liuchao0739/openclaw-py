"""Shared parameter types for embedded-agent run orchestration."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

EmbeddedRunTrigger = Literal["cron", "heartbeat", "manual", "memory", "overflow", "user"]


class CurrentInboundPromptContext(TypedDict, total=False):
    text: str
    resumableText: str
    promptJoiner: Literal["\n\n", "\n", " "]


class RunEmbeddedAgentParams(TypedDict, total=False):
    sessionId: str
    sessionKey: str
    lifecycleGeneration: str
    promptCacheKey: str
    sandboxSessionKey: str
    agentId: str
    messageChannel: str
    messageProvider: str
    trigger: EmbeddedRunTrigger
    jobId: str
    memoryFlushWritePath: str
    sessionFile: str
    workspaceDir: str
    cwd: str
    config: dict[str, Any]
    prompt: str
    transcriptPrompt: str
    currentInboundContext: CurrentInboundPromptContext
    provider: str
    model: str
    timeoutMs: int
    runTimeoutOverrideMs: int
    runId: str
    authProfileId: str
    disableTools: bool