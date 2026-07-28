from __future__ import annotations

from typing import Any


def build_contract_shared() -> dict[str, Any]:
    return {
        "version": 1,
        "schemas": {},
        "validations": [],
    }


def validate_contract(
    contract: dict[str, Any],
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    return True, None
