from __future__ import annotations

from typing import Any


def _check_cron_expression(expr: str) -> dict[str, Any] | None:
    parts = expr.strip().split()
    if len(parts) != 5:
        return {"valid": False, "error": f"Cron expression must have 5 parts, got {len(parts)}"}
    return None


def validate_cron_expression(expr: str) -> dict[str, Any]:
    result = _check_cron_expression(expr)
    if result:
        return result
    return {"valid": True}


async def list_cron_jobs(
    config: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rt = runtime or {}
    cfg = config or {}
    cron = cfg.get("cron") or {}
    jobs = cron.get("jobs") or []
    return jobs
