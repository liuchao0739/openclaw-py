from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecToolConfig(BaseModel):
    host: str | None = None
    mode: str | None = None
    security: str | None = None
    ask: str | None = None
    node: str | None = None
    path_prepend: list[str] | None = Field(default=None, alias="pathPrepend")
    safe_bins: list[str] | None = Field(default=None, alias="safeBins")
    strict_inline_eval: bool | None = Field(
        default=None, alias="strictInlineEval"
    )
    command_highlighting: bool | None = Field(
        default=None, alias="commandHighlighting"
    )
    safe_bin_trusted_dirs: list[str] | None = Field(
        default=None, alias="safeBinTrustedDirs"
    )
    safe_bin_profiles: dict[str, Any] | None = Field(
        default=None, alias="safeBinProfiles"
    )
    reviewer: dict[str, Any] | None = None
    background_ms: int | None = Field(default=None, alias="backgroundMs")
    timeout_sec: int | None = Field(default=None, alias="timeoutSec")
    approval_running_notice_ms: int | None = Field(
        default=None, alias="approvalRunningNoticeMs"
    )
    cleanup_ms: int | None = Field(default=None, alias="cleanupMs")
    notify_on_exit: bool | None = Field(default=None, alias="notifyOnExit")
    notify_on_exit_empty_success: bool | None = Field(
        default=None, alias="notifyOnExitEmptySuccess"
    )
    apply_patch: dict[str, Any] | None = Field(default=None, alias="applyPatch")

    model_config = {"populate_by_name": True, "extra": "allow"}


class FsToolsConfig(BaseModel):
    workspace_only: bool | None = Field(default=None, alias="workspaceOnly")


class SessionsSpawnToolsConfig(BaseModel):
    attachments: dict[str, Any] | None = None


class ToolPolicyConfig(BaseModel):
    allow: list[str] | None = None
    also_allow: list[str] | None = Field(default=None, alias="alsoAllow")
    deny: list[str] | None = None
    profile: str | None = None


class GroupToolPolicyConfig(BaseModel):
    allow: list[str] | None = None
    also_allow: list[str] | None = Field(default=None, alias="alsoAllow")
    deny: list[str] | None = None


class MediaUnderstandingConfig(BaseModel):
    enabled: bool | None = None
    scope: dict[str, Any] | None = None
    max_bytes: int | None = Field(default=None, alias="maxBytes")
    max_chars: int | None = Field(default=None, alias="maxChars")
    prompt: str | None = None
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    language: str | None = None
    attachments: dict[str, Any] | None = None
    models: list[dict[str, Any]] | None = None
    echo_transcript: bool | None = Field(default=None, alias="echoTranscript")
    echo_format: str | None = Field(default=None, alias="echoFormat")

    model_config = {"populate_by_name": True, "extra": "allow"}


class MediaToolsConfig(BaseModel):
    models: list[dict[str, Any]] | None = None
    concurrency: int | None = None
    image: MediaUnderstandingConfig | None = None
    audio: MediaUnderstandingConfig | None = None
    video: MediaUnderstandingConfig | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class LinkToolsConfig(BaseModel):
    enabled: bool | None = None
    scope: dict[str, Any] | None = None
    max_links: int | None = Field(default=None, alias="maxLinks")
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    models: list[dict[str, Any]] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ToolLoopDetectionConfig(BaseModel):
    enabled: bool | None = None
    history_size: int | None = Field(default=None, alias="historySize")
    warning_threshold: int | None = Field(default=None, alias="warningThreshold")
    unknown_tool_threshold: int | None = Field(
        default=None, alias="unknownToolThreshold"
    )
    critical_threshold: int | None = Field(default=None, alias="criticalThreshold")
    global_circuit_breaker_threshold: int | None = Field(
        default=None, alias="globalCircuitBreakerThreshold"
    )
    detectors: dict[str, Any] | None = None
    post_compaction_guard: dict[str, Any] | None = Field(
        default=None, alias="postCompactionGuard"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class MessageToolsConfig(BaseModel):
    allow_cross_context_send: bool | None = Field(
        default=None, alias="allowCrossContextSend"
    )
    cross_context: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    broadcast: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentToolsConfig(BaseModel):
    profile: str | None = None
    allow: list[str] | None = None
    also_allow: list[str] | None = Field(default=None, alias="alsoAllow")
    deny: list[str] | None = None
    by_provider: dict[str, ToolPolicyConfig] | None = Field(
        default=None, alias="byProvider"
    )
    tools_by_sender: dict[str, GroupToolPolicyConfig] | None = Field(
        default=None, alias="toolsBySender"
    )
    code_mode: dict[str, Any] | None = Field(default=None, alias="codeMode")
    elevated: dict[str, Any] | None = None
    exec: ExecToolConfig | None = None
    fs: FsToolsConfig | None = None
    loop_detection: ToolLoopDetectionConfig | None = Field(
        default=None, alias="loopDetection"
    )
    message: MessageToolsConfig | None = None
    sandbox: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ToolsConfig(BaseModel):
    profile: str | None = None
    allow: list[str] | None = None
    also_allow: list[str] | None = Field(default=None, alias="alsoAllow")
    deny: list[str] | None = None
    by_provider: dict[str, ToolPolicyConfig] | None = Field(
        default=None, alias="byProvider"
    )
    tools_by_sender: dict[str, GroupToolPolicyConfig] | None = Field(
        default=None, alias="toolsBySender"
    )
    web: dict[str, Any] | None = None
    media: MediaToolsConfig | None = None
    links: LinkToolsConfig | None = None
    message: MessageToolsConfig | None = None
    agent_to_agent: dict[str, Any] | None = Field(
        default=None, alias="agentToAgent"
    )
    sessions: dict[str, Any] | None = None
    elevated: dict[str, Any] | None = None
    exec: ExecToolConfig | None = None
    fs: FsToolsConfig | None = None
    loop_detection: ToolLoopDetectionConfig | None = Field(
        default=None, alias="loopDetection"
    )
    tool_search: dict[str, Any] | None = Field(default=None, alias="toolSearch")
    code_mode: dict[str, Any] | None = Field(default=None, alias="codeMode")
    sessions_spawn: SessionsSpawnToolsConfig | None = Field(
        default=None, alias="sessions_spawn"
    )
    subagents: dict[str, Any] | None = None
    sandbox: dict[str, Any] | None = None
    experimental: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}
