"""Preemptive compaction route types."""

from __future__ import annotations

from typing import Literal

PreemptiveCompactionRoute = Literal[
    "fits",
    "compact_only",
    "truncate_tool_results_only",
    "compact_then_truncate",
]