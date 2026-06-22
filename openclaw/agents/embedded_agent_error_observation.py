"""Sanitized API error fields for failover logging (minimal port)."""

from __future__ import annotations

from typing import Any, TypedDict


class ApiErrorObservationFields(TypedDict, total=False):
    rawErrorPreview: str | None
    providerRuntimeFailureKind: str | None


def sanitize_for_console(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        text = str(value)
    else:
        text = value
    text = text.replace("\n", " ").strip()
    if len(text) > 200:
        text = text[:197] + "..."
    return text or None


def build_api_error_observation_fields(raw_error: object) -> ApiErrorObservationFields:
    preview = sanitize_for_console(raw_error) if raw_error is not None else None
    return {
        "rawErrorPreview": preview,
        "providerRuntimeFailureKind": None,
    }


def should_suppress_raw_error_console_suffix(provider_runtime_failure_kind: str | None) -> bool:
    return False