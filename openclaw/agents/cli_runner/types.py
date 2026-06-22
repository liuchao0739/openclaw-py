"""Shared types for preparing and executing CLI-backed agent runs (partial)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

CliBackendExecutionMode = Literal["normal", "side_question"]

class RunCliAgentParams(TypedDict, total=False):
    sessionId: str
    sessionKey: str
    workspaceDir: str
    cwd: str
    config: dict[str, Any]
    prompt: str
    executionMode: CliBackendExecutionMode
    provider: str
    model: str
    timeoutMs: int
    runTimeoutOverrideMs: int
    runId: str
    cliSessionId: str
    authProfileId: str
    toolsAllow: list[str]
    disableTools: bool