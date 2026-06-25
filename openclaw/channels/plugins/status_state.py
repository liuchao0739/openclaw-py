"""Human-readable channel status-state labels for status output."""

from __future__ import annotations


def format_channel_status_state(status_state: str) -> str:
    """Format a status state into a human-readable label."""
    labels = {
        "linked": "linked",
        "not-linked": "not linked",
        "unstable": "auth stabilizing",
    }
    return labels.get(status_state, status_state)
