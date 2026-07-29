from .provider_id import normalize_lowercase_string_or_empty


def normalize_model_catalog_provider_id(provider: str) -> str:
    return normalize_lowercase_string_or_empty(provider)


def build_model_catalog_ref(provider: str, model_id: str) -> str:
    return f"{normalize_model_catalog_provider_id(provider)}/{model_id}"


def build_model_catalog_merge_key(provider: str, model_id: str) -> str:
    return f"{normalize_model_catalog_provider_id(provider)}::{normalize_lowercase_string_or_empty(model_id)}"
