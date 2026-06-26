"""Origin class for plugin discovery and runtime trust decisions.

Mirrors src/plugins/plugin-origin.types.ts.
"""

from __future__ import annotations

from typing import Literal

PluginOrigin = Literal["bundled", "global", "workspace", "config"]
