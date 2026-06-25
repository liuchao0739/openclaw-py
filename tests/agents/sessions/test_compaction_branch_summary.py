"""Tests for agents/sessions/compaction — branch summarization."""

from __future__ import annotations

import pytest

from openclaw.agents.sessions.compaction.branch_summarization import (
    collect_entries_for_branch_summary,
    generate_branch_summary,
)


class _StubSession:
    def __init__(self, branches: dict[str, list[dict]]):
        self._branches = branches

    def get_branch(self, leaf_id: str) -> list[dict]:
        return self._branches.get(leaf_id, [])


class TestCollectEntriesForBranchSummary:
    def test_no_old_leaf_returns_empty(self):
        session = _StubSession({})
        result = collect_entries_for_branch_summary(session, None, "target")
        assert result["entries"] == []
        assert result["commonAncestorId"] is None

    def test_collects_diff_entries(self):
        session = _StubSession({
            "old": [
                {"id": "a", "text": "common"},
                {"id": "b", "text": "old-only"},
            ],
            "target": [
                {"id": "a", "text": "common"},
                {"id": "c", "text": "target-only"},
            ],
        })
        result = collect_entries_for_branch_summary(session, "old", "target")
        assert result["commonAncestorId"] == "a"
        diff_ids = [e["id"] for e in result["entries"]]
        assert "c" in diff_ids
        assert "a" not in diff_ids

    def test_no_common_ancestor(self):
        session = _StubSession({
            "old": [{"id": "b", "text": "old-only"}],
            "target": [{"id": "c", "text": "target-only"}],
        })
        result = collect_entries_for_branch_summary(session, "old", "target")
        assert result["commonAncestorId"] is None
        assert len(result["entries"]) == 1
        assert result["entries"][0]["id"] == "c"


class TestGenerateBranchSummary:
    async def test_returns_error_when_runtime_unavailable(self):
        result = await generate_branch_summary([], {"apiKey": "key", "model": None})
        assert "error" in result
