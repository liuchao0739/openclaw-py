"""Builds the stable diagnostic/session execution id for a single cron run.

Mirrors src/cron/run-id.ts.
"""

from __future__ import annotations


def create_cron_execution_id(job_id: str, started_at: int) -> str:
    """Build the stable execution id for a single cron run."""
    return f"cron:{job_id}:{started_at}"
