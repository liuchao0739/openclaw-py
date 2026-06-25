"""Groups channel-scoped status issues for status report table rendering."""

from __future__ import annotations

from typing import Any


def group_channel_issues_by_channel(
    issues: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group issue-like rows by channel id while preserving the original issue order per channel."""
    by_channel: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        key = issue.get("channel", "")
        if key in by_channel:
            by_channel[key].append(issue)
        else:
            by_channel[key] = [issue]
    return by_channel
