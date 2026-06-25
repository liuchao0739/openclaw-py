"""Shared status issue helpers for channel plugins."""

from __future__ import annotations

from typing import Any


def format_status_issue(
    channel: str,
    issue_type: str,
    message: str,
    *,
    severity: str = "warning",
    account_id: str | None = None,
) -> dict[str, Any]:
    """Format a channel status issue for diagnostics."""
    issue: dict[str, Any] = {
        "channel": channel,
        "type": issue_type,
        "message": message,
        "severity": severity,
    }
    if account_id:
        issue["accountId"] = account_id
    return issue


def is_critical_issue(issue: dict[str, Any]) -> bool:
    """Check if a status issue is critical."""
    return issue.get("severity") == "error"


def deduplicate_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate issues by channel + type + accountId."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = f"{issue.get('channel')}:{issue.get('type')}:{issue.get('accountId', '')}"
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result
