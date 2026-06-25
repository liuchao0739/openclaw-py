"""Shared channel action helpers.

Filters token-backed accounts and composes account-level action gates.
"""

from __future__ import annotations

from typing import Any, Callable


def list_token_sourced_accounts(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out accounts explicitly marked as tokenless."""
    return [acc for acc in accounts if acc.get("tokenSource") != "none"]


def create_union_action_gate(
    accounts: list[dict[str, Any]],
    create_gate: Callable[[dict[str, Any]], Callable[..., bool]],
) -> Callable[..., bool]:
    """Create an action gate enabled when any account-level gate enables the action."""
    gates = [create_gate(acc) for acc in accounts]

    def gate(key: str, default_value: bool = True) -> bool:
        return any(g(key, default_value) for g in gates)

    return gate
