"""Named queue lanes for work that must not interleave with the main command stream.

Mirrors src/process/lanes.ts.
"""

from __future__ import annotations

from enum import Enum


class CommandLane(str, Enum):
    Main = "main"
    Cron = "cron"
    CronNested = "cron-nested"
    Subagent = "subagent"
    Nested = "nested"
