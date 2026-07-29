from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    provider: str | None = None
    profile: str | None = None

    model_config = {"extra": "allow"}


class PluginsConfig(BaseModel):
    entries: dict[str, Any] | None = None
    allow_list: list[str] | None = Field(default=None, alias="allowList")
    install: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class SkillsConfig(BaseModel):
    entries: dict[str, Any] | None = None
    max_prompt_chars: int | None = Field(default=None, alias="maxPromptChars")

    model_config = {"extra": "allow"}


class HooksConfig(BaseModel):
    entries: dict[str, Any] | None = None
    queue: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class BrowserConfig(BaseModel):
    enabled: bool | None = None
    driver: str | None = None

    model_config = {"extra": "allow"}


class CliConfig(BaseModel):
    defaults: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class CommitmentsConfig(BaseModel):
    enabled: bool | None = None
    auto_extract: bool | None = Field(default=None, alias="autoExtract")

    model_config = {"extra": "allow"}


class NodeHostConfig(BaseModel):
    enabled: bool | None = None
    allow_commands: list[str] | None = Field(default=None, alias="allowCommands")

    model_config = {"extra": "allow"}


class MemoryConfig(BaseModel):
    enabled: bool | None = None
    sources: list[str] | None = None

    model_config = {"extra": "allow"}


class McpConfig(BaseModel):
    servers: dict[str, Any] | None = None
    codex: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class TtsConfig(BaseModel):
    provider: str | None = None
    voice: str | None = None

    model_config = {"extra": "allow"}


class MessagesConfig(BaseModel):
    tts: TtsConfig | None = None
    group_chat: dict[str, Any] | None = Field(default=None, alias="groupChat")

    model_config = {"extra": "allow"}


class ApprovalsConfig(BaseModel):
    enabled: bool | None = None
    mode: str | None = None

    model_config = {"extra": "allow"}


class CronConfig(BaseModel):
    enabled: bool | None = None
    retention: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class AccessGroupsConfig(BaseModel):
    groups: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class AcpConfig(BaseModel):
    enabled: bool | None = None
    dispatch: dict[str, Any] | None = None
    backend: str | None = None
    fallbacks: list[str] | None = None
    default_agent: str | None = Field(default=None, alias="defaultAgent")
    allowed_agents: list[str] | None = Field(default=None, alias="allowedAgents")
    max_concurrent_sessions: int | None = Field(
        default=None, alias="maxConcurrentSessions"
    )
    stream: dict[str, Any] | None = None
    runtime: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class CrestodianConfig(BaseModel):
    enabled: bool | None = None

    model_config = {"extra": "allow"}
