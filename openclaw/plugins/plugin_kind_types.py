"""Plugin kind labels for non-provider plugin capability groups.

Mirrors src/plugins/plugin-kind.types.ts.
"""

from __future__ import annotations

from typing import Literal

PluginKind = Literal["memory", "context-engine"]
