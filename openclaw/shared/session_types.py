"""Gateway session listing and usage types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class GatewayAgentIdentity:
    name: str | None = None
    theme: str | None = None
    emoji: str | None = None
    avatar: str | None = None
    avatar_url: str | None = None


@dataclass
class GatewayAgentModel:
    primary: str | None = None
    fallbacks: list[str] | None = None


@dataclass
class GatewayAgentRuntime:
    id: str
    fallback: str | None = None
    source: str | None = None


@dataclass
class GatewayThinkingLevelOption:
    id: str
    label: str


@dataclass
class GatewayAgentRow:
    id: str
    name: str | None = None
    identity: GatewayAgentIdentity | None = None
    workspace: str | None = None
    model: GatewayAgentModel | None = None
    agent_runtime: GatewayAgentRuntime | None = None
    thinking_levels: list[GatewayThinkingLevelOption] | None = None
    thinking_options: list[str] | None = None
    thinking_default: str | None = None
