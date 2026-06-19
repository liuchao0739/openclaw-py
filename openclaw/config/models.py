"""OpenClaw configuration models (minimal MVP subset)."""

from __future__ import annotations

from typing import Any

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


class OpenClawConfig(BaseModel):
    """Top-level OpenClaw config (MVP subset; expands per migration phase."""

    gateway: GatewayConfig | None = None
    agents: AgentsConfig | None = None
    models: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
