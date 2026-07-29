from __future__ import annotations

from typing import Any


def resolve_message_secret_scope(params: dict) -> list[str]:
    return params.get("scopes", [])


def validate_message_secret_scope(scopes: list[str]) -> bool:
    return all(isinstance(s, str) and s for s in scopes)
