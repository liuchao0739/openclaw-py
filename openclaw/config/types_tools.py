from __future__ import annotations

from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class ExecToolConfig(BaseModel):
    host: Optional[str] = None
    mode: Optional[str] = None
    security: Optional[str] = None
    ask: Optional[str] = None
    node: Optional[str] = None
    path_prepend: Optional[List[str]] = Field(default=None, alias="pathPrepend")
    safe_bins: Optional[List[str]] = Field(default=None, alias="safeBins")
    strict_inline_eval: Optional[bool] = Field(
        default=None, alias="strictInlineEval"
    )
    command_highlighting: Optional[bool] = Field(
        default=None, alias="commandHighlighting"
    )
    safe_bin_trusted_dirs: Optional[List[str]] = Field(
        default=None, alias="safeBinTrustedDirs"
    )
    safe_bin_profiles: Optional[Dict[str, Any]] = Field(
        default=None, alias="safeBinProfiles"
    )
    reviewer: Optional[Dict[str, Any]] = None
    background_ms: Optional[int] = Field(default=None, alias="backgroundMs")
    timeout_sec: Optional[int] = Field(default=None, alias="timeoutSec")
    approval_running_notice_ms: Optional[int] = Field(
        default=None, alias="approvalRunningNoticeMs"
    )
    cleanup_ms: Optional[int] = Field(default=None, alias="cleanupMs")
    notify_on_exit: Optional[bool] = Field(default=None, alias="notifyOnExit")
    notify_on_exit_empty_success: Optional[bool] = Field(
        default=None, alias="notifyOnExitEmptySuccess"
    )
    apply_patch: Optional[Dict[str, Any]] = Field(default=None, alias="applyPatch")

    model_config = {"populate_by_name": True, "extra": "allow"}


class FsToolsConfig(BaseModel):
    workspace_only: Optional[bool] = Field(default=None, alias="workspaceOnly")


class SessionsSpawnToolsConfig(BaseModel):
    attachments: Optional[Dict[str, Any]] = None


class ToolPolicyConfig(BaseModel):
    allow: Optional[List[str]] = None
    also_allow: Optional[List[str]] = Field(default=None, alias="alsoAllow")
    deny: Optional[List[str]] = None
    profile: Optional[str] = None


class GroupToolPolicyConfig(BaseModel):
    allow: Optional[List[str]] = None
    also_allow: Optional[List[str]] = Field(default=None, alias="alsoAllow")
    deny: Optional[List[str]] = None


class MediaUnderstandingConfig(BaseModel):
    enabled: Optional[bool] = None
    scope: Optional[Dict[str, Any]] = None
    max_bytes: Optional[int] = Field(default=None, alias="maxBytes")
    max_chars: Optional[int] = Field(default=None, alias="maxChars")
    prompt: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, alias="timeoutSeconds")
    language: Optional[str] = None
    attachments: Optional[Dict[str, Any]] = None
    models: Optional[List[Dict[str, Any]]] = None
    echo_transcript: Optional[bool] = Field(default=None, alias="echoTranscript")
    echo_format: Optional[str] = Field(default=None, alias="echoFormat")

    model_config = {"populate_by_name": True, "extra": "allow"}


class MediaToolsConfig(BaseModel):
    models: Optional[List[Dict[str, Any]]] = None
    concurrency: Optional[int] = None
    image: Optional[MediaUnderstandingConfig] = None
    audio: Optional[MediaUnderstandingConfig] = None
    video: Optional[MediaUnderstandingConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class LinkToolsConfig(BaseModel):
    enabled: Optional[bool] = None
    scope: Optional[Dict[str, Any]] = None
    max_links: Optional[int] = Field(default=None, alias="maxLinks")
    timeout_seconds: Optional[int] = Field(default=None, alias="timeoutSeconds")
    models: Optional[List[Dict[str, Any]]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ToolLoopDetectionConfig(BaseModel):
    enabled: Optional[bool] = None
    history_size: Optional[int] = Field(default=None, alias="historySize")
    warning_threshold: Optional[int] = Field(default=None, alias="warningThreshold")
    unknown_tool_threshold: Optional[int] = Field(
        default=None, alias="unknownToolThreshold"
    )
    critical_threshold: Optional[int] = Field(default=None, alias="criticalThreshold")
    global_circuit_breaker_threshold: Optional[int] = Field(
        default=None, alias="globalCircuitBreakerThreshold"
    )
    detectors: Optional[Dict[str, Any]] = None
    post_compaction_guard: Optional[Dict[str, Any]] = Field(
        default=None, alias="postCompactionGuard"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class MessageToolsConfig(BaseModel):
    allow_cross_context_send: Optional[bool] = Field(
        default=None, alias="allowCrossContextSend"
    )
    cross_context: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    broadcast: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentToolsConfig(BaseModel):
    profile: Optional[str] = None
    allow: Optional[List[str]] = None
    also_allow: Optional[List[str]] = Field(default=None, alias="alsoAllow")
    deny: Optional[List[str]] = None
    by_provider: Optional[Dict[str, ToolPolicyConfig]] = Field(
        default=None, alias="byProvider"
    )
    tools_by_sender: Optional[Dict[str, GroupToolPolicyConfig]] = Field(
        default=None, alias="toolsBySender"
    )
    code_mode: Optional[Dict[str, Any]] = Field(default=None, alias="codeMode")
    elevated: Optional[Dict[str, Any]] = None
    exec: Optional[ExecToolConfig] = None
    fs: Optional[FsToolsConfig] = None
    loop_detection: Optional[ToolLoopDetectionConfig] = Field(
        default=None, alias="loopDetection"
    )
    message: Optional[MessageToolsConfig] = None
    sandbox: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ToolsConfig(BaseModel):
    profile: Optional[str] = None
    allow: Optional[List[str]] = None
    also_allow: Optional[List[str]] = Field(default=None, alias="alsoAllow")
    deny: Optional[List[str]] = None
    by_provider: Optional[Dict[str, ToolPolicyConfig]] = Field(
        default=None, alias="byProvider"
    )
    tools_by_sender: Optional[Dict[str, GroupToolPolicyConfig]] = Field(
        default=None, alias="toolsBySender"
    )
    web: Optional[Dict[str, Any]] = None
    media: Optional[MediaToolsConfig] = None
    links: Optional[LinkToolsConfig] = None
    message: Optional[MessageToolsConfig] = None
    agent_to_agent: Optional[Dict[str, Any]] = Field(
        default=None, alias="agentToAgent"
    )
    sessions: Optional[Dict[str, Any]] = None
    elevated: Optional[Dict[str, Any]] = None
    exec: Optional[ExecToolConfig] = None
    fs: Optional[FsToolsConfig] = None
    loop_detection: Optional[ToolLoopDetectionConfig] = Field(
        default=None, alias="loopDetection"
    )
    tool_search: Optional[Dict[str, Any]] = Field(default=None, alias="toolSearch")
    code_mode: Optional[Dict[str, Any]] = Field(default=None, alias="codeMode")
    sessions_spawn: Optional[SessionsSpawnToolsConfig] = Field(
        default=None, alias="sessions_spawn"
    )
    subagents: Optional[Dict[str, Any]] = None
    sandbox: Optional[Dict[str, Any]] = None
    experimental: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}
