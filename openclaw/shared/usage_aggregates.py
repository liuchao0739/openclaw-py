"""Usage aggregate helpers accumulate token, cost, and latency usage totals."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LatencyTotals:
    count: int = 0
    sum: float = 0.0
    min: float = float("inf")
    max: float = 0.0
    p95_max: float = 0.0


@dataclass
class DailyLatency:
    date: str
    count: int = 0
    sum: float = 0.0
    min: float = float("inf")
    max: float = 0.0
    p95_max: float = 0.0


def merge_usage_latency(
    totals: LatencyTotals,
    latency: dict[str, Any] | None = None,
) -> None:
    if not latency or latency.get("count", 0) <= 0:
        return
    count = latency["count"]
    totals.count += count
    totals.sum += latency.get("avgMs", 0) * count
    totals.min = min(totals.min, latency.get("minMs", float("inf")))
    totals.max = max(totals.max, latency.get("maxMs", 0))
    totals.p95_max = max(totals.p95_max, latency.get("p95Ms", 0))


def merge_usage_daily_latency(
    daily_latency_map: dict[str, DailyLatency],
    daily_latency: list[dict[str, Any]] | None = None,
) -> None:
    if not daily_latency:
        return
    for day in daily_latency:
        date = day.get("date", "")
        existing = daily_latency_map.get(date)
        if existing is None:
            existing = DailyLatency(date=date)
            daily_latency_map[date] = existing
        count = day.get("count", 0)
        existing.count += count
        existing.sum += day.get("avgMs", 0) * count
        existing.min = min(existing.min, day.get("minMs", float("inf")))
        existing.max = max(existing.max, day.get("maxMs", 0))
        existing.p95_max = max(existing.p95_max, day.get("p95Ms", 0))


def build_usage_aggregate_tail(
    by_channel_map: dict[str, dict[str, Any]],
    latency_totals: LatencyTotals,
    daily_latency_map: dict[str, DailyLatency],
    model_daily_map: dict[str, dict[str, Any]],
    daily_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_channel = sorted(
        [{"channel": k, "totals": v} for k, v in by_channel_map.items()],
        key=lambda a: a["totals"].get("totalCost", 0),
        reverse=True,
    )

    latency = None
    if latency_totals.count > 0:
        latency_avg = latency_totals.sum / latency_totals.count if latency_totals.count > 0 else 0
        latency_min = 0 if latency_totals.min == float("inf") else latency_totals.min
        latency = {
            "count": latency_totals.count,
            "avgMs": latency_avg,
            "minMs": latency_min,
            "maxMs": latency_totals.max,
            "p95Ms": latency_totals.p95_max,
        }

    daily_latency = sorted(
        [
            {
                "date": entry.date,
                "count": entry.count,
                "avgMs": entry.sum / entry.count if entry.count > 0 else 0,
                "minMs": 0 if entry.min == float("inf") else entry.min,
                "maxMs": entry.max,
                "p95Ms": entry.p95_max,
            }
            for entry in daily_latency_map.values()
        ],
        key=lambda a: a["date"],
    )

    model_daily = sorted(
        list(model_daily_map.values()),
        key=lambda a: (a.get("date", ""), -a.get("cost", 0)),
    )

    daily = sorted(
        list(daily_map.values()),
        key=lambda a: a.get("date", ""),
    )

    return {
        "byChannel": by_channel,
        "latency": latency,
        "dailyLatency": daily_latency,
        "modelDaily": model_daily,
        "daily": daily,
    }
