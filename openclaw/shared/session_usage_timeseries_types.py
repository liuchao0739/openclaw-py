"""Session usage time series types for sampling and charting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionUsageTimePoint:
    timestamp: int
    input: int
    output: int
    cache_read: int
    cache_write: int
    total_tokens: int
    cost: float
    cumulative_tokens: int
    cumulative_cost: float


@dataclass
class SessionUsageTimeSeries:
    session_id: str | None = None
    points: list[SessionUsageTimePoint] = field(default_factory=list)
