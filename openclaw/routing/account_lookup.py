"""Account lookup helpers resolve route accounts from normalized account ids.

Mirrors src/routing/account-lookup.ts.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from openclaw.infra.prototype_keys import is_blocked_object_key
from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty
from openclaw.routing.account_id import normalize_optional_account_id

T = TypeVar("T")


def resolve_account_entry(
    accounts: dict[str, T] | None,
    account_id: str,
) -> T | None:
    if not accounts or not isinstance(accounts, dict):
        return None
    if account_id in accounts:
        return accounts[account_id]
    normalized = normalize_lowercase_string_or_empty(account_id)
    for key, value in accounts.items():
        if normalize_lowercase_string_or_empty(key) == normalized:
            return value
    return None


def resolve_normalized_account_entry(
    accounts: dict[str, T] | None,
    account_id: str,
    normalize_account_id_fn: Callable[[str], str],
) -> T | None:
    if not accounts or not isinstance(accounts, dict):
        return None
    if account_id in accounts and not is_blocked_object_key(account_id):
        return accounts[account_id]
    normalized = normalize_account_id_fn(account_id)
    for key, value in accounts.items():
        if is_blocked_object_key(key):
            continue
        candidate = normalize_account_id_fn(key)
        if (
            normalize_optional_account_id(key)
            and not is_blocked_object_key(candidate)
            and candidate == normalized
        ):
            return value
    return None
