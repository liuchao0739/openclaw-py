"""Branch-summary bridge from session managers to the shared agent-core summarizer.

Keeps session-manager branch traversal local while delegating summary generation to agent-core.

The agent-core runtime and session-manager are resolved lazily; when unavailable
the functions return empty results so callers can wire branch summarization
without crashes during the migration window.
"""

from __future__ import annotations

from typing import Any, TypedDict


class CollectEntriesResult(TypedDict):
    entries: list[dict[str, Any]]
    commonAncestorId: str | None


class BranchSummaryResult(TypedDict, total=False):
    summary: str
    readFiles: list[str]
    modifiedFiles: list[str]
    aborted: bool
    error: str


class GenerateBranchSummaryOptions(TypedDict, total=False):
    model: Any
    apiKey: str
    headers: dict[str, str]
    signal: Any
    customInstructions: str
    replaceInstructions: bool
    reserveTokens: int


def collect_entries_for_branch_summary(
    session: Any,
    old_leaf_id: str | None,
    target_id: str,
) -> CollectEntriesResult:
    """Collect entries that differ between two session branches for summarization."""
    if not old_leaf_id:
        return {"entries": [], "commonAncestorId": None}

    old_branch = session.get_branch(old_leaf_id) if hasattr(session, "get_branch") else []
    target_path = session.get_branch(target_id) if hasattr(session, "get_branch") else []
    return _collect_entries_for_branch_summary_from_branches(old_branch, target_path)


def _collect_entries_for_branch_summary_from_branches(
    old_branch: list[dict[str, Any]],
    target_path: list[dict[str, Any]],
) -> CollectEntriesResult:
    """Collect entries from two branch paths, returning the diff and common ancestor."""
    old_ids = {e.get("id") for e in old_branch if isinstance(e, dict)}
    target_ids = {e.get("id") for e in target_path if isinstance(e, dict)}
    common = old_ids & target_ids

    common_ancestor_id: str | None = None
    for entry in reversed(old_branch):
        if isinstance(entry, dict) and entry.get("id") in common:
            common_ancestor_id = entry.get("id")
            break

    diff_entries = [
        e for e in target_path
        if isinstance(e, dict) and e.get("id") not in common
    ]
    return {"entries": diff_entries, "commonAncestorId": common_ancestor_id}


async def generate_branch_summary(
    entries: list[dict[str, Any]],
    options: GenerateBranchSummaryOptions,
) -> BranchSummaryResult:
    """Generate a human-readable branch summary through the shared agent-core runtime."""
    try:
        from openclaw.agents.runtime import (
            generate_branch_summary as generate_branch_summary_core,
            openClawAgentCoreRuntime,
        )

        result = await generate_branch_summary_core(
            entries,
            {"runtime": openClawAgentCoreRuntime, **options},
        )
        if result.get("ok"):
            return result["value"]
        error = result.get("error", {})
        if error.get("code") == "aborted":
            return {"aborted": True, "error": error.get("message", "")}
        return {"error": error.get("message", "")}
    except Exception as exc:
        return {"error": str(exc)}
