"""Gateway connect-error detail helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConnectErrorDetailCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_UNAUTHORIZED = "AUTH_UNAUTHORIZED"
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_MISMATCH = "AUTH_TOKEN_MISMATCH"
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
    PAIRING_REQUIRED = "PAIRING_REQUIRED"
    CLIENT_VERSION_MISMATCH = "CLIENT_VERSION_MISMATCH"


class ConnectPairingRequiredReason(StrEnum):
    NOT_PAIRED = "not-paired"
    ROLE_UPGRADE = "role-upgrade"
    SCOPE_UPGRADE = "scope-upgrade"
    METADATA_UPGRADE = "metadata-upgrade"


class ConnectErrorDetails(BaseModel):
    code: ConnectErrorDetailCode | None = None
    message: str | None = None
    pairing_reason: ConnectPairingRequiredReason | None = Field(
        default=None, alias="pairingReason"
    )
    recovery_next_step: str | None = Field(default=None, alias="recoveryNextStep")
    scopes: list[str] | None = None
    roles: list[str] | None = None

    model_config = {"populate_by_name": True}


def normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def normalize_connect_error_details(raw: dict[str, Any]) -> ConnectErrorDetails:
    code_raw = normalize_optional_string(raw.get("code"))
    code = ConnectErrorDetailCode(code_raw) if code_raw in ConnectErrorDetailCode.__members__.values() else None
    pairing_raw = normalize_optional_string(raw.get("pairingReason"))
    pairing = (
        ConnectPairingRequiredReason(pairing_raw)
        if pairing_raw in ConnectPairingRequiredReason.__members__.values()
        else None
    )
    return ConnectErrorDetails(
        code=code,
        message=normalize_optional_string(raw.get("message")),
        pairing_reason=pairing,
        recovery_next_step=normalize_optional_string(raw.get("recoveryNextStep")),
        scopes=_normalize_string_list(raw.get("scopes")),
        roles=_normalize_string_list(raw.get("roles")),
    )


def _normalize_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = [s for item in value if (s := normalize_optional_string(item))]
    return items or None
