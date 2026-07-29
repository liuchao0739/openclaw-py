from __future__ import annotations

from openclaw.routing.account_id import normalize_optional_account_id


def normalize_account_id(value: str | None = None) -> str | None:
    return normalize_optional_account_id(value)
