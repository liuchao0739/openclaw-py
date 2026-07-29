from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SecurityAuditSuppression(BaseModel):
    check_id: str = Field(alias="checkId")
    title_includes: str | None = Field(default=None, alias="titleIncludes")
    detail_includes: str | None = Field(default=None, alias="detailIncludes")
    reason: str | None = None

    model_config = {"populate_by_name": True}


class SecurityConfig(BaseModel):
    audit: dict[str, Any] | None = None
    install_policy: dict[str, Any] | None = Field(default=None, alias="installPolicy")

    model_config = {"populate_by_name": True, "extra": "allow"}


class MetaConfig(BaseModel):
    last_touched_version: str | None = Field(default=None, alias="lastTouchedVersion")
    last_touched_at: str | None = Field(default=None, alias="lastTouchedAt")

    model_config = {"populate_by_name": True}


class EnvConfig(BaseModel):
    shell_env: dict[str, Any] | None = Field(default=None, alias="shellEnv")
    vars: dict[str, str] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class WizardConfig(BaseModel):
    last_run_at: str | None = Field(default=None, alias="lastRunAt")
    last_run_version: str | None = Field(default=None, alias="lastRunVersion")
    last_run_commit: str | None = Field(default=None, alias="lastRunCommit")
    last_run_command: str | None = Field(default=None, alias="lastRunCommand")
    last_run_mode: str | None = Field(default=None, alias="lastRunMode")

    model_config = {"populate_by_name": True}


class UpdateAutoConfig(BaseModel):
    enabled: bool | None = None
    stable_delay_hours: int | None = Field(default=None, alias="stableDelayHours")
    stable_jitter_hours: int | None = Field(default=None, alias="stableJitterHours")
    beta_check_interval_hours: int | None = Field(default=None, alias="betaCheckIntervalHours")

    model_config = {"populate_by_name": True}


class UpdateConfig(BaseModel):
    channel: str | None = None
    check_on_start: bool | None = Field(default=None, alias="checkOnStart")
    auto: UpdateAutoConfig | None = None

    model_config = {"populate_by_name": True}


class UiAssistantConfig(BaseModel):
    name: str | None = None
    avatar: str | None = None


class UiConfig(BaseModel):
    seam_color: str | None = Field(default=None, alias="seamColor")
    assistant: UiAssistantConfig | None = None

    model_config = {"populate_by_name": True}


class TuiFooterConfig(BaseModel):
    show_remote_host: bool | None = Field(default=None, alias="showRemoteHost")

    model_config = {"populate_by_name": True}


class TuiConfig(BaseModel):
    footer: TuiFooterConfig | None = None

    model_config = {"populate_by_name": True}


class MediaConfig(BaseModel):
    preserve_filenames: bool | None = Field(default=None, alias="preserveFilenames")
    ttl_hours: int | None = Field(default=None, alias="ttlHours")

    model_config = {"populate_by_name": True}


class OpenClawConfig(BaseModel):
    schema: str | None = Field(default=None, alias="$schema")
    meta: MetaConfig | None = None
    auth: dict[str, Any] | None = None
    access_groups: dict[str, Any] | None = Field(default=None, alias="accessGroups")
    acp: dict[str, Any] | None = None
    env: EnvConfig | dict[str, Any] | None = None
    wizard: WizardConfig | None = None
    diagnostics: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    security: SecurityConfig | None = None
    cli: dict[str, Any] | None = None
    crestodian: dict[str, Any] | None = None
    update: UpdateConfig | None = None
    browser: dict[str, Any] | None = None
    ui: UiConfig | None = None
    tui: TuiConfig | None = None
    secrets: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
    surfaces: dict[str, Any] | None = None
    models: dict[str, Any] | None = None
    node_host: dict[str, Any] | None = Field(default=None, alias="nodeHost")
    agents: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None
    bindings: list[dict[str, Any]] | None = None
    broadcast: dict[str, Any] | None = None
    audio: dict[str, Any] | None = None
    media: MediaConfig | None = None
    messages: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None
    approvals: dict[str, Any] | None = None
    session: dict[str, Any] | None = None
    web: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    cron: dict[str, Any] | None = None
    transcripts: dict[str, Any] | None = None
    commitments: dict[str, Any] | None = None
    hooks: dict[str, Any] | None = None
    discovery: dict[str, Any] | None = None
    talk: dict[str, Any] | None = None
    gateway: dict[str, Any] | None = None
    memory: dict[str, Any] | None = None
    mcp: dict[str, Any] | None = None
    proxy: dict[str, Any] | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class OpenClawConfigInput(OpenClawConfig):
    pass
