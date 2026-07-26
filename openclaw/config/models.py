"""OpenClaw configuration models (minimal MVP subset)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GatewayAuthConfig(BaseModel):
    token: str | None = None
    password: str | None = None


class GatewayServerConfig(BaseModel):
    port: int = 18789
    bind: str = "loopback"
    auth: GatewayAuthConfig | None = None


class GatewayConfig(BaseModel):
    port: int | None = None
    bind: str | None = None
    auth: GatewayAuthConfig | None = None
    server: GatewayServerConfig | None = None

    def resolved_port(self) -> int:
        if self.server and self.server.port:
            return self.server.port
        return self.port or 18789


class AgentsDefaultsConfig(BaseModel):
    model: str | None = None
    workspace: str | None = None


class AgentsConfig(BaseModel):
    defaults: AgentsDefaultsConfig | None = None


class AcpDispatchConfig(BaseModel):
    enabled: bool | None = None


class AcpStreamConfig(BaseModel):
    coalesce_idle_ms: int | None = Field(default=None, alias="coalesceIdleMs")
    max_chunk_chars: int | None = Field(default=None, alias="maxChunkChars")
    repeat_suppression: bool | None = Field(default=None, alias="repeatSuppression")
    delivery_mode: Literal["live", "final_only"] | None = Field(default=None, alias="deliveryMode")
    hidden_boundary_separator: Literal["none", "space", "newline", "paragraph"] | None = Field(
        default=None, alias="hiddenBoundarySeparator"
    )
    max_output_chars: int | None = Field(default=None, alias="maxOutputChars")
    max_session_update_chars: int | None = Field(default=None, alias="maxSessionUpdateChars")
    tag_visibility: dict[str, bool] | None = Field(default=None, alias="tagVisibility")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AcpRuntimeConfig(BaseModel):
    ttl_minutes: int | None = Field(default=None, alias="ttlMinutes")
    """Operator install/setup command shown by `/acp install` and `/acp doctor`."""
    install_command: str | None = Field(default=None, alias="installCommand")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AcpConfig(BaseModel):
    enabled: bool | None = None
    dispatch: AcpDispatchConfig | None = None
    """Backend id registered by an ACP runtime plugin (for example: acpx)."""
    backend: str | None = None
    """Backend ids tried when the primary backend fails with UNAVAILABLE."""
    fallbacks: list[str] | None = None
    default_agent: str | None = Field(default=None, alias="defaultAgent")
    allowed_agents: list[str] | None = Field(default=None, alias="allowedAgents")
    max_concurrent_sessions: int | None = Field(default=None, alias="maxConcurrentSessions")
    stream: AcpStreamConfig | None = None
    runtime: AcpRuntimeConfig | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class OpenClawConfig(BaseModel):
    """Top-level OpenClaw config (MVP subset; expands per migration phase."""

    gateway: GatewayConfig | None = None
    agents: AgentsConfig | None = None
    acp: AcpConfig | None = None
    models: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
