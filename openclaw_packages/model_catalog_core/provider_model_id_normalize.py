"""Provider-specific model id normalization rules.

Mirrors packages/model-catalog-core/src/provider-model-id-normalize.ts.
"""

from __future__ import annotations

ANTIGRAVITY_BARE_PRO_IDS: frozenset[str] = frozenset(
    {"gemini-3-pro", "gemini-3.1-pro", "gemini-3-1-pro"},
)
GOOGLE_PROVIDER_PREFIX = "google/"


def normalize_google_preview_model_id(model_id: str) -> str:
    if model_id.startswith(GOOGLE_PROVIDER_PREFIX):
        inner = model_id[len(GOOGLE_PROVIDER_PREFIX) :]
        normalized_inner = normalize_google_preview_model_id(inner)
        return (
            model_id
            if normalized_inner == inner
            else f"{GOOGLE_PROVIDER_PREFIX}{normalized_inner}"
        )
    if model_id in ("gemini-3-pro", "gemini-3-pro-preview"):
        return "gemini-3.1-pro-preview"
    if model_id == "gemini-3-flash":
        return "gemini-3-flash-preview"
    if model_id == "gemini-3.1-pro":
        return "gemini-3.1-pro-preview"
    if model_id == "gemini-3.1-flash-lite-preview":
        return "gemini-3.1-flash-lite"
    if model_id in ("gemini-3.1-flash", "gemini-3.1-flash-preview"):
        return "gemini-3-flash-preview"
    if model_id == "gemma-4-26b":
        return "gemma-4-26b-a4b-it"
    return model_id


def normalize_together_model_id(model_id: str) -> str:
    if model_id == "moonshotai/Kimi-K2.5":
        return "moonshotai/Kimi-K2.6"
    return model_id


def normalize_antigravity_preview_model_id(model_id: str) -> str:
    if model_id in ANTIGRAVITY_BARE_PRO_IDS:
        return f"{model_id}-low"
    return model_id


__all__ = [
    "normalize_antigravity_preview_model_id",
    "normalize_google_preview_model_id",
    "normalize_together_model_id",
]
