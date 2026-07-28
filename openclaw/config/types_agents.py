from __future__ import annotations

from typing import Any, Optional, List, Dict, Union

from pydantic import BaseModel, Field


class AgentRuntimeAcpConfig(BaseModel):
    agent: Optional[str] = None
    backend: Optional[str] = None
    mode: Optional[str] = None
    cwd: Optional[str] = None

    model_config = {"extra": "allow"}


class AgentRuntimeConfig(BaseModel):
    type: str
    acp: Optional[AgentRuntimeAcpConfig] = None

    model_config = {"extra": "allow"}


class AgentBindingMatch(BaseModel):
    channel: str
    account_id: Optional[str] = Field(default=None, alias="accountId")
    peer: Optional[Dict[str, Any]] = None
    guild_id: Optional[str] = Field(default=None, alias="guildId")
    team_id: Optional[str] = Field(default=None, alias="teamId")
    roles: Optional[List[str]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentRouteBinding(BaseModel):
    type: Optional[str] = None
    agent_id: str = Field(alias="agentId")
    comment: Optional[str] = None
    match: AgentBindingMatch
    session: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentAcpBinding(BaseModel):
    type: str
    agent_id: str = Field(alias="agentId")
    comment: Optional[str] = None
    match: AgentBindingMatch
    acp: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentModelConfig(BaseModel):
    primary: Optional[str] = None
    fallbacks: Optional[List[str]] = None

    model_config = {"extra": "allow"}


class AgentDefaultsConfig(BaseModel):
    thinking_default: Optional[str] = Field(default=None, alias="thinkingDefault")
    verbose_default: Optional[str] = Field(default=None, alias="verboseDefault")
    tool_progress_detail: Optional[str] = Field(default=None, alias="toolProgressDetail")
    reasoning_default: Optional[str] = Field(default=None, alias="reasoningDefault")
    fast_mode_default: Optional[bool] = Field(default=None, alias="fastModeDefault")
    context_injection: Optional[str] = Field(default=None, alias="contextInjection")
    bootstrap_max_chars: Optional[int] = Field(default=None, alias="bootstrapMaxChars")
    bootstrap_total_max_chars: Optional[int] = Field(
        default=None, alias="bootstrapTotalMaxChars"
    )
    experimental: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    heartbeat: Optional[Dict[str, Any]] = None
    compaction: Optional[Dict[str, Any]] = None
    run_retries: Optional[Dict[str, Any]] = Field(default=None, alias="runRetries")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentContextLimitsConfig(BaseModel):
    max_chars: Optional[int] = Field(default=None, alias="maxChars")
    max_chars_per_message: Optional[int] = Field(
        default=None, alias="maxCharsPerMessage"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentModelEntryConfig(BaseModel):
    agent_runtime: Optional[Dict[str, Any]] = Field(
        default=None, alias="agentRuntime"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class EmbeddedAgentExecutionContract(BaseModel):
    pass


class AgentConfig(BaseModel):
    id: str
    default: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    workspace: Optional[str] = None
    agent_dir: Optional[str] = Field(default=None, alias="agentDir")
    model: Optional[AgentModelConfig] = None
    models: Optional[Dict[str, AgentModelEntryConfig]] = None
    thinking_default: Optional[str] = Field(default=None, alias="thinkingDefault")
    verbose_default: Optional[str] = Field(default=None, alias="verboseDefault")
    tool_progress_detail: Optional[str] = Field(default=None, alias="toolProgressDetail")
    reasoning_default: Optional[str] = Field(default=None, alias="reasoningDefault")
    fast_mode_default: Optional[bool] = Field(default=None, alias="fastModeDefault")
    context_injection: Optional[str] = Field(default=None, alias="contextInjection")
    bootstrap_max_chars: Optional[int] = Field(default=None, alias="bootstrapMaxChars")
    bootstrap_total_max_chars: Optional[int] = Field(
        default=None, alias="bootstrapTotalMaxChars"
    )
    experimental: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    memory_search: Optional[Dict[str, Any]] = Field(default=None, alias="memorySearch")
    human_delay: Optional[Dict[str, Any]] = Field(default=None, alias="humanDelay")
    tts: Optional[Dict[str, Any]] = None
    skills_limits: Optional[Dict[str, Any]] = Field(default=None, alias="skillsLimits")
    context_limits: Optional[AgentContextLimitsConfig] = Field(
        default=None, alias="contextLimits"
    )
    context_tokens: Optional[int] = Field(default=None, alias="contextTokens")
    heartbeat: Optional[Dict[str, Any]] = None
    identity: Optional[Dict[str, Any]] = None
    group_chat: Optional[Dict[str, Any]] = Field(default=None, alias="groupChat")
    subagents: Optional[Dict[str, Any]] = None
    run_retries: Optional[Dict[str, Any]] = Field(default=None, alias="runRetries")
    embedded_agent: Optional[Dict[str, Any]] = Field(default=None, alias="embeddedAgent")
    sandbox: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    runtime: Optional[AgentRuntimeConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentsConfig(BaseModel):
    defaults: Optional[AgentDefaultsConfig] = None
    list: Optional[List[AgentConfig]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


AgentBinding = Union[AgentRouteBinding, AgentAcpBinding]
