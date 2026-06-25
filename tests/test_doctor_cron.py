"""Tests for commands/doctor/cron — dreaming payload migration."""

from __future__ import annotations

from openclaw.commands.doctor.cron import (
    count_stale_dreaming_jobs,
    migrate_legacy_dreaming_payload_shape,
)
from openclaw.commands.doctor.cron.dreaming_payload_migration import (
    MANAGED_MEMORY_DREAMING_CRON_NAME,
    MANAGED_MEMORY_DREAMING_CRON_TAG,
    MEMORY_DREAMING_SYSTEM_EVENT_TEXT,
)


def _make_stale_job() -> dict:
    return {
        "name": MANAGED_MEMORY_DREAMING_CRON_NAME,
        "payload": {
            "kind": "systemEvent",
            "text": MEMORY_DREAMING_SYSTEM_EVENT_TEXT,
        },
        "sessionTarget": "main",
        "delivery": {"mode": "channel"},
    }


def _make_current_job() -> dict:
    return {
        "name": MANAGED_MEMORY_DREAMING_CRON_NAME,
        "payload": {
            "kind": "agentTurn",
            "message": MEMORY_DREAMING_SYSTEM_EVENT_TEXT,
            "lightContext": True,
        },
        "sessionTarget": "isolated",
        "delivery": {"mode": "none"},
    }


class TestCountStale:
    def test_empty(self):
        assert count_stale_dreaming_jobs([]) == 0

    def test_no_dreaming_jobs(self):
        jobs = [{"name": "other-job"}]
        assert count_stale_dreaming_jobs(jobs) == 0

    def test_stale_job(self):
        assert count_stale_dreaming_jobs([_make_stale_job()]) == 1

    def test_current_job_not_stale(self):
        assert count_stale_dreaming_jobs([_make_current_job()]) == 0

    def test_mixed(self):
        jobs = [_make_stale_job(), _make_current_job(), _make_stale_job()]
        assert count_stale_dreaming_jobs(jobs) == 2

    def test_tagged_description(self):
        job = {"description": f"Job {MANAGED_MEMORY_DREAMING_CRON_TAG}", "sessionTarget": "main"}
        assert count_stale_dreaming_jobs([job]) == 1


class TestMigrate:
    def test_empty(self):
        result = migrate_legacy_dreaming_payload_shape([])
        assert result["changed"] is False
        assert result["rewrittenCount"] == 0

    def test_migrate_stale(self):
        jobs = [_make_stale_job()]
        result = migrate_legacy_dreaming_payload_shape(jobs)
        assert result["changed"] is True
        assert result["rewrittenCount"] == 1
        assert jobs[0]["sessionTarget"] == "isolated"
        assert jobs[0]["payload"]["kind"] == "agentTurn"
        assert jobs[0]["payload"]["lightContext"] is True
        assert jobs[0]["delivery"]["mode"] == "none"

    def test_skip_current(self):
        jobs = [_make_current_job()]
        result = migrate_legacy_dreaming_payload_shape(jobs)
        assert result["changed"] is False
        assert result["rewrittenCount"] == 0

    def test_skip_non_dreaming(self):
        jobs = [{"name": "other"}]
        result = migrate_legacy_dreaming_payload_shape(jobs)
        assert result["changed"] is False

    def test_mixed_migration(self):
        stale = _make_stale_job()
        current = _make_current_job()
        result = migrate_legacy_dreaming_payload_shape([stale, current])
        assert result["rewrittenCount"] == 1
        assert stale["sessionTarget"] == "isolated"
        assert current["sessionTarget"] == "isolated"  # Already correct
