"""Resolves whether an account-scoped action is enabled."""

from __future__ import annotations

from typing import Any, Callable


def create_account_action_gate(
    base_actions: dict[str, bool] | None = None,
    account_actions: dict[str, bool] | None = None,
) -> Callable[..., bool]:
    """Create an action gate where account-specific flags override channel-level defaults."""

    def gate(key: str, default_value: bool = True) -> bool:
        if account_actions and key in account_actions:
            return account_actions[key] is not False
        if base_actions and key in base_actions:
            return base_actions[key] is not False
        return default_value

    return gate
