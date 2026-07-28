from __future__ import annotations

import re
from typing import Any, Optional

from .string_utils import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

SECRET_REF_SOURCES = frozenset(["env", "file", "exec"])
DEFAULT_SECRET_PROVIDER_ALIAS = "default"
ENV_SECRET_REF_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
LEGACY_SECRETREF_ENV_MARKER_PREFIX = "secretref-env:"
ENV_SECRET_TEMPLATE_RE = re.compile(r"^\$\{([A-Z][A-Z0-9_]{0,127})\}$")


def is_record(value: object) -> bool:
    return isinstance(value, dict)


def normalize_secret_input_string(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def has_secret_ref_source(value: object) -> bool:
    return isinstance(value, str) and value in SECRET_REF_SOURCES


def has_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and len(value.strip()) > 0


def is_secret_ref(value: object) -> bool:
    if not is_record(value):
        return False
    keys = list(value.keys())
    return (
        len(keys) == 3
        and has_secret_ref_source(value.get("source"))
        and has_non_empty_string(value.get("provider"))
        and has_non_empty_string(value.get("id"))
    )


def is_legacy_secret_ref_without_provider(value: object) -> bool:
    if not is_record(value):
        return False
    return (
        has_secret_ref_source(value.get("source"))
        and has_non_empty_string(value.get("id"))
        and "provider" not in value
    )


def parse_env_template_secret_ref(value: object) -> Optional[dict]:
    if not isinstance(value, str):
        return None
    match = ENV_SECRET_TEMPLATE_RE.match(value.strip())
    if not match:
        return None
    return {
        "source": "env",
        "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
        "id": match.group(1) or "",
    }


def parse_legacy_secret_ref_env_marker(value: object) -> Optional[dict]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed.startswith(LEGACY_SECRETREF_ENV_MARKER_PREFIX):
        return None
    secret_id = trimmed[len(LEGACY_SECRETREF_ENV_MARKER_PREFIX):]
    if not ENV_SECRET_REF_ID_RE.match(secret_id):
        return None
    return {
        "source": "env",
        "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
        "id": secret_id,
    }


def coerce_secret_ref(value: object) -> Optional[dict]:
    if is_secret_ref(value):
        return dict(value)
    if is_legacy_secret_ref_without_provider(value):
        return {
            "source": value["source"],
            "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
            "id": value["id"],
        }
    return parse_env_template_secret_ref(value) or parse_legacy_secret_ref_env_marker(value)


def has_configured_secret_input(value: object) -> bool:
    if normalize_secret_input_string(value):
        return True
    return coerce_secret_ref(value) is not None


def format_secret_ref_label(ref: dict) -> str:
    return f"{ref['source']}:{ref['provider']}:{ref['id']}"


def create_unresolved_secret_input_error(path: str, ref: dict) -> Exception:
    return ValueError(
        f'{path}: unresolved SecretRef "{format_secret_ref_label(ref)}". '
        f"Resolve this command against an active gateway runtime snapshot before reading it."
    )


def resolve_secret_input_ref(value: object) -> Optional[dict]:
    return coerce_secret_ref(value)


def normalize_resolved_secret_input_string(value: object, path: str) -> Optional[str]:
    normalized = normalize_secret_input_string(value)
    if normalized:
        return normalized
    ref = resolve_secret_input_ref(value)
    if not ref:
        return None
    raise create_unresolved_secret_input_error(path, ref)


def normalize_env_secret_input_string(value: object) -> Optional[str]:
    return normalize_secret_input_string(value)
