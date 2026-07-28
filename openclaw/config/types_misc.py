from __future__ import annotations

from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    provider: Optional[str] = None
    profile: Optional[str] = None

    model_config = {"extra": "allow"}


class PluginsConfig(BaseModel):
    entries: Optional[Dict[str, Any]] = None
    allow_list: Optional[List[str]] = Field(default=None, alias="allowList")
    install: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class SkillsConfig(BaseModel):
    entries: Optional[Dict[str, Any]] = None
    max_prompt_chars: Optional[int] = Field(default=None, alias="maxPromptChars")

    model_config = {"extra": "allow"}


class HooksConfig(BaseModel):
    entries: Optional[Dict[str, Any]] = None
    queue: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class BrowserConfig(BaseModel):
    enabled: Optional[bool] = None
    driver: Optional[str] = None

    model_config = {"extra": "allow"}


class CliConfig(BaseModel):
    defaults: Optional[Dict[str, Any]] = None
    commands: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class CommitmentsConfig(BaseModel):
    enabled: Optional[bool] = None
    auto_extract: Optional[bool] = Field(default=None, alias="autoExtract")

    model_config = {"extra": "allow"}


class NodeHostConfig(BaseModel):
    enabled: Optional[bool] = None
    allow_commands: Optional[List[str]] = Field(default=None, alias="allowCommands")

    model_config = {"extra": "allow"}


class MemoryConfig(BaseModel):
    enabled: Optional[bool] = None
    sources: Optional[List[str]] = None

    model_config = {"extra": "allow"}


class McpConfig(BaseModel):
    servers: Optional[Dict[str, Any]] = None
    codex: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class TtsConfig(BaseModel):
    provider: Optional[str] = None
    voice: Optional[str] = None

    model_config = {"extra": "allow"}


class MessagesConfig(BaseModel):
    tts: Optional[TtsConfig] = None
    group_chat: Optional[Dict[str, Any]] = Field(default=None, alias="groupChat")

    model_config = {"extra": "allow"}


class ApprovalsConfig(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None

    model_config = {"extra": "allow"}


class CronConfig(BaseModel):
    enabled: Optional[bool] = None
    retention: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class AccessGroupsConfig(BaseModel):
    groups: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class AcpConfig(BaseModel):
    enabled: Optional[bool] = None
    dispatch: Optional[Dict[str, Any]] = None
    backend: Optional[str] = None
    fallbacks: Optional[List[str]] = None
    default_agent: Optional[str] = Field(default=None, alias="defaultAgent")
    allowed_agents: Optional[List[str]] = Field(default=None, alias="allowedAgents")
    max_concurrent_sessions: Optional[int] = Field(
        default=None, alias="maxConcurrentSessions"
    )
    stream: Optional[Dict[str, Any]] = None
    runtime: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class CrestodianConfig(BaseModel):
    enabled: Optional[bool] = None

    model_config = {"extra": "allow"}
