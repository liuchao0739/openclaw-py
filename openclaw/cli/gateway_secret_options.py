from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string


def resolve_gateway_secret_options(params: dict) -> dict[str, str | None]:
    return {
        "token": normalize_optional_string(params.get("token")),
        "apiKey": normalize_optional_string(params.get("apiKey")),
    }
