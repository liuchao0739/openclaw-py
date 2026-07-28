"""OpenClaw configuration models (minimal MVP subset)."""

from __future__ import annotations

from typing import Any, Literal, Optional, List, Dict

from pydantic import BaseModel, Field


class GatewayAuthConfig(BaseModel):
    token: Optional[str] = None
    password: Optional[str] = None


class GatewayServerConfig(BaseModel):
    port: int = 18789
    bind: str = "loopback"
    auth: Optional[GatewayAuthConfig] = None


class GatewayConfig(BaseModel):
    port: Optional[int] = None
    bind: Optional[str] = None
    auth: Optional[GatewayAuthConfig] = None
    server: Optional[GatewayServerConfig] = None

    def resolved_port(self) -> int:
        if self.server and self.server.port:
            return self.server.port
        return self.port or 18789


class AgentsDefaultsConfig(BaseModel):
    model: Optional[str] = None
    workspace: Optional[str] = None


class AgentsConfig(BaseModel):
    defaults: Optional[AgentsDefaultsConfig] = None


class AcpDispatchConfig(BaseModel):
    enabled: Optional[bool] = None


class AcpStreamConfig(BaseModel):
    coalesce_idle_ms: Optional[int] = Field(default=None, alias="coalesceIdleMs")
    max_chunk_chars: Optional[int] = Field(default=None, alias="maxChunkChars")
    repeat_suppression: Optional[bool] = Field(default=None, alias="repeatSuppression")
    delivery_mode: Optional[Literal["live", "final_only"]] = Field(default=None, alias="deliveryMode")
    hidden_boundary_separator: Optional[Literal["none", "space", "newline", "paragraph"]] = Field(
        default=None, alias="hiddenBoundarySeparator"
    )
    max_output_chars: Optional[int] = Field(default=None, alias="maxOutputChars")
    max_session_update_chars: Optional[int] = Field(default=None, alias="maxSessionUpdateChars")
    tag_visibility: Optional[Dict[str, bool]] = Field(default=None, alias="tagVisibility")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AcpRuntimeConfig(BaseModel):
    ttl_minutes: Optional[int] = Field(default=None, alias="ttlMinutes")
    """Operator install/setup command shown by `/acp install` and `/acp doctor`."""
    install_command: Optional[str] = Field(default=None, alias="installCommand")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AcpConfig(BaseModel):
    enabled: Optional[bool] = None
    dispatch: Optional[AcpDispatchConfig] = None
    """Backend id registered by an ACP runtime plugin (for example: acpx)."""
    backend: Optional[str] = None
    """Backend ids tried when the primary backend fails with UNAVAILABLE."""
    fallbacks: Optional[List[str]] = None
    default_agent: Optional[str] = Field(default=None, alias="defaultAgent")
    allowed_agents: Optional[List[str]] = Field(default=None, alias="allowedAgents")
    max_concurrent_sessions: Optional[int] = Field(default=None, alias="maxConcurrentSessions")
    stream: Optional[AcpStreamConfig] = None
    runtime: Optional[AcpRuntimeConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class OpenClawConfig(BaseModel):
    """Top-level OpenClaw config (MVP subset; expands per migration phase."""

    gateway: Optional[GatewayConfig] = None
    agents: Optional[AgentsConfig] = None
    acp: Optional[AcpConfig] = None
    models: Optional[Dict[str, Any]] = None
    channels: Optional[Dict[str, Any]] = None
    plugins: Optional[Dict[str, Any]] = None
    skills: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
