"""Account enabled predicate.

Mirrors src/shared/account-enabled.ts.
"""

from __future__ import annotations

from typing import Any, Mapping


def is_account_enabled(account: Any) -> bool:
    """Check if an account is enabled. Returns True for non-objects or when enabled != False."""
    if not isinstance(account, Mapping):
        return True
    return account.get("enabled") is not False
