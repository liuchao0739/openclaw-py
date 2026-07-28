from __future__ import annotations

from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class SecurityAuditSuppression(BaseModel):
    check_id: str = Field(alias="checkId")
    title_includes: Optional[str] = Field(default=None, alias="titleIncludes")
    detail_includes: Optional[str] = Field(default=None, alias="detailIncludes")
    reason: Optional[str] = None

    model_config = {"populate_by_name": True}


class SecurityConfig(BaseModel):
    audit: Optional[Dict[str, Any]] = None
    install_policy: Optional[Dict[str, Any]] = Field(default=None, alias="installPolicy")

    model_config = {"populate_by_name": True, "extra": "allow"}


class MetaConfig(BaseModel):
    last_touched_version: Optional[str] = Field(default=None, alias="lastTouchedVersion")
    last_touched_at: Optional[str] = Field(default=None, alias="lastTouchedAt")

    model_config = {"populate_by_name": True}


class EnvConfig(BaseModel):
    shell_env: Optional[Dict[str, Any]] = Field(default=None, alias="shellEnv")
    vars: Optional[Dict[str, str]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class WizardConfig(BaseModel):
    last_run_at: Optional[str] = Field(default=None, alias="lastRunAt")
    last_run_version: Optional[str] = Field(default=None, alias="lastRunVersion")
    last_run_commit: Optional[str] = Field(default=None, alias="lastRunCommit")
    last_run_command: Optional[str] = Field(default=None, alias="lastRunCommand")
    last_run_mode: Optional[str] = Field(default=None, alias="lastRunMode")

    model_config = {"populate_by_name": True}


class UpdateAutoConfig(BaseModel):
    enabled: Optional[bool] = None
    stable_delay_hours: Optional[int] = Field(default=None, alias="stableDelayHours")
    stable_jitter_hours: Optional[int] = Field(default=None, alias="stableJitterHours")
    beta_check_interval_hours: Optional[int] = Field(default=None, alias="betaCheckIntervalHours")

    model_config = {"populate_by_name": True}


class UpdateConfig(BaseModel):
    channel: Optional[str] = None
    check_on_start: Optional[bool] = Field(default=None, alias="checkOnStart")
    auto: Optional[UpdateAutoConfig] = None

    model_config = {"populate_by_name": True}


class UiAssistantConfig(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None


class UiConfig(BaseModel):
    seam_color: Optional[str] = Field(default=None, alias="seamColor")
    assistant: Optional[UiAssistantConfig] = None

    model_config = {"populate_by_name": True}


class TuiFooterConfig(BaseModel):
    show_remote_host: Optional[bool] = Field(default=None, alias="showRemoteHost")

    model_config = {"populate_by_name": True}


class TuiConfig(BaseModel):
    footer: Optional[TuiFooterConfig] = None

    model_config = {"populate_by_name": True}


class MediaConfig(BaseModel):
    preserve_filenames: Optional[bool] = Field(default=None, alias="preserveFilenames")
    ttl_hours: Optional[int] = Field(default=None, alias="ttlHours")

    model_config = {"populate_by_name": True}


class OpenClawConfig(BaseModel):
    schema: Optional[str] = Field(default=None, alias="$schema")
    meta: Optional[MetaConfig] = None
    auth: Optional[Dict[str, Any]] = None
    access_groups: Optional[Dict[str, Any]] = Field(default=None, alias="accessGroups")
    acp: Optional[Dict[str, Any]] = None
    env: Optional[EnvConfig | Dict[str, Any]] = None
    wizard: Optional[WizardConfig] = None
    diagnostics: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    security: Optional[SecurityConfig] = None
    cli: Optional[Dict[str, Any]] = None
    crestodian: Optional[Dict[str, Any]] = None
    update: Optional[UpdateConfig] = None
    browser: Optional[Dict[str, Any]] = None
    ui: Optional[UiConfig] = None
    tui: Optional[TuiConfig] = None
    secrets: Optional[Dict[str, Any]] = None
    skills: Optional[Dict[str, Any]] = None
    plugins: Optional[Dict[str, Any]] = None
    surfaces: Optional[Dict[str, Any]] = None
    models: Optional[Dict[str, Any]] = None
    node_host: Optional[Dict[str, Any]] = Field(default=None, alias="nodeHost")
    agents: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    bindings: Optional[List[Dict[str, Any]]] = None
    broadcast: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    media: Optional[MediaConfig] = None
    messages: Optional[Dict[str, Any]] = None
    commands: Optional[Dict[str, Any]] = None
    approvals: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    web: Optional[Dict[str, Any]] = None
    channels: Optional[Dict[str, Any]] = None
    cron: Optional[Dict[str, Any]] = None
    transcripts: Optional[Dict[str, Any]] = None
    commitments: Optional[Dict[str, Any]] = None
    hooks: Optional[Dict[str, Any]] = None
    discovery: Optional[Dict[str, Any]] = None
    talk: Optional[Dict[str, Any]] = None
    gateway: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    mcp: Optional[Dict[str, Any]] = None
    proxy: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow", "populate_by_name": True}


class OpenClawConfigInput(OpenClawConfig):
    pass
