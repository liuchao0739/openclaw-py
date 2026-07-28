from __future__ import annotations

import math
from typing import Any

DEFAULT_CRON_MAX_CONCURRENT_RUNS = 8


def resolve_cron_max_concurrent_runs(cron_config: dict[str, Any] | None = None) -> int:
    raw = (cron_config or {}).get("maxConcurrentRuns")
    if isinstance(raw, (int, float)) and math.isfinite(raw):
        return max(1, int(raw))
    return DEFAULT_CRON_MAX_CONCURRENT_RUNS
