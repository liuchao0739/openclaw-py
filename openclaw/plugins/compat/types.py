"""Plugin compatibility types describe lifecycle status for plugin migration
and deprecation checks.

Mirrors src/plugins/compat/types.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PluginCompatStatus = Literal["active", "deprecated", "removal-pending", "removed"]
PluginCompatOwner = Literal[
    "agent-runtime", "channel", "config", "core",
    "plugin-execution", "provider", "sdk", "setup",
]


@dataclass
class PluginCompatRecord:
    """A plugin compatibility lifecycle record."""

    code: str
    status: str
    owner: str
    introduced: str
    docs_path: str
    deprecated: str | None = None
    warning_starts: str | None = None
    remove_after: str | None = None
    replacement: str | None = None
    surfaces: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    release_note: str | None = None
