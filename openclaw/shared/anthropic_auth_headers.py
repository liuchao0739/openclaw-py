"""Anthropic auth header helpers detect foundry bearer auth and strip credentials."""

from __future__ import annotations

import re
from typing import Any


def uses_foundry_bearer_auth(provider: str | None, auth_header: bool | None, headers: dict[str, str] | None) -> bool:
    if provider != "microsoft-foundry":
        return False
    if auth_header is True:
        return True
    return _has_bearer_authorization_header(headers)


def _has_bearer_authorization_header(headers: dict[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        if key.lower() == "authorization" and re.match(r"^bearer\s+\S+", value.strip(), re.IGNORECASE):
            return True
    return False


def omit_foundry_bearer_credential_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
    if not headers:
        return None
    next_headers: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in ("authorization", "x-api-key", "api-key"):
            continue
        next_headers[key] = value
    return next_headers if len(next_headers) > 0 else None
