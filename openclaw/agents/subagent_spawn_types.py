"""Shared spawn mode enums for subagent session tool, registry, and announce."""

from __future__ import annotations

from typing import Literal

SUBAGENT_SPAWN_MODES = ("run", "session")
SpawnSubagentMode = Literal["run", "session"]

SUBAGENT_SPAWN_SANDBOX_MODES = ("inherit", "require")
SpawnSubagentSandboxMode = Literal["inherit", "require"]

SUBAGENT_SPAWN_CONTEXT_MODES = ("isolated", "fork")
SpawnSubagentContextMode = Literal["isolated", "fork"]
