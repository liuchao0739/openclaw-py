"""Stable model catalog ref and merge-key builders.

Mirrors packages/model-catalog-core/src/model-catalog-refs.ts.
"""

from __future__ import annotations

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty


def normalize_model_catalog_provider_id(provider: str) -> str:
    return normalize_lowercase_string_or_empty(provider)


def build_model_catalog_ref(provider: str, model_id: str) -> str:
    return f"{normalize_model_catalog_provider_id(provider)}/{model_id}"


def build_model_catalog_merge_key(provider: str, model_id: str) -> str:
    return (
        f"{normalize_model_catalog_provider_id(provider)}"
        f"::{normalize_lowercase_string_or_empty(model_id)}"
    )


__all__ = [
    "build_model_catalog_merge_key",
    "build_model_catalog_ref",
    "normalize_model_catalog_provider_id",
]
