"""Shared loose cron fixtures for isolated-agent tests.

Mirrors src/cron/isolated-agent/job-fixtures.ts.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def make_isolated_agent_job_fixture(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a loose cron job fixture for isolated-agent unit tests."""
    base: dict[str, Any] = {
        "id": "test-job",
        "name": "Test Job",
        "schedule": {"kind": "cron", "expr": "0 9 * * *", "tz": "UTC"},
        "sessionTarget": "isolated",
        "payload": {"kind": "agentTurn", "message": "test"},
    }
    if overrides:
        merged = deepcopy(base)
        merged.update(deepcopy(overrides))
        return merged
    return base


def make_isolated_agent_params_fixture(
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a loose cron params fixture for isolated-agent unit tests.

    If ``overrides`` contains a ``job`` key, it is used as job-level overrides.
    """
    job_overrides: dict[str, Any] | None = None
    if overrides and "job" in overrides:
        job_overrides = overrides["job"] if isinstance(overrides["job"], dict) else None

    base: dict[str, Any] = {
        "cfg": {},
        "deps": {},
        "job": make_isolated_agent_job_fixture(job_overrides),
        "message": "test",
        "sessionKey": "cron:test",
    }
    if overrides:
        merged = deepcopy(base)
        for k, v in overrides.items():
            if k == "job":
                merged["job"] = make_isolated_agent_job_fixture(
                    v if isinstance(v, dict) else None
                )
            else:
                merged[k] = deepcopy(v)
        return merged
    return base
