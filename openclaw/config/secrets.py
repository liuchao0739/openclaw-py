"""Secret reference helpers (subset of config/types.secrets)."""

from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.types import SecretRef
from openclaw.utils.normalize_secret_input import normalize_optional_secret_input

# Max sane expiry ms (~ year 275760)
MAX_DATE_TIMESTAMP_MS = 8_640_000_000_000_000


def coerce_secret_ref(value: Any) -> SecretRef | None:
    if not value or not isinstance(value, dict):
        return None
    source = value.get("source")
    provider = value.get("provider")
    ref_id = value.get("id")
    if not isinstance(source, str) or not isinstance(provider, str) or not isinstance(ref_id, str):
        return None
    if not source.strip() or not provider.strip() or not ref_id.strip():
        return None
    return SecretRef(source=source.strip(), provider=provider.strip(), id=ref_id.strip())


def normalize_secret_input_string(value: Any) -> str | None:
    return normalize_optional_secret_input(value)