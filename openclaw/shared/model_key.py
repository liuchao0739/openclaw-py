"""Model key helpers join provider and model into canonical key."""

from __future__ import annotations


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def model_key(provider: str, model: str) -> str:
    provider_id = provider.strip()
    model_id = model.strip()
    if not provider_id:
        return model_id
    if not model_id:
        return provider_id
    if _normalize_lowercase_or_empty(model_id).startswith(f"{_normalize_lowercase_or_empty(provider_id)}/"):
        return model_id
    return f"{provider_id}/{model_id}"
