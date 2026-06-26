"""Formats a short human-readable disjunction such as 'A, B, or C'.

Mirrors src/shared/human-list.ts.
"""

from __future__ import annotations


def format_human_list(values: list[str]) -> str:
    """Format a list of strings as a human-readable disjunction."""
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return f"{', '.join(values[:-1])}, or {values[-1]}"
