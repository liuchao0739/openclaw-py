"""Resolves provider/model prompt-cache retention behavior."""

from __future__ import annotations

from typing import Any, Literal

CacheRetention = Literal["none", "short", "long"]


def is_google_prompt_cache_eligible(*, model_api: str | None = None, model_id: str | None = None) -> bool:
    if model_api != "google-generative-ai":
        return False
    mid = (model_id or "").strip().lower()
    return mid.startswith("gemini-2.5") or mid.startswith("gemini-3")


def _is_anthropic_family(provider: str, model_api: str | None, model_id: str | None) -> bool:
    p = provider.strip().lower()
    if p in ("anthropic", "claude"):
        return True
    if model_api in ("anthropic-messages",):
        return True
    mid = (model_id or "").strip().lower()
    return mid.startswith("claude-")


def resolve_cache_retention(
    extra_params: dict[str, Any] | None,
    provider: str,
    *,
    model_api: str | None = None,
    model_id: str | None = None,
    supports_prompt_cache_key: bool | None = None,
) -> CacheRetention | None:
    has_explicit = extra_params and (
        extra_params.get("cacheRetention") is not None
        or extra_params.get("cacheControlTtl") is not None
    )
    family = _is_anthropic_family(provider, model_api, model_id) and has_explicit
    google = is_google_prompt_cache_eligible(model_api=model_api, model_id=model_id)
    cache_key = supports_prompt_cache_key is True
    if not family and not google and not cache_key:
        return None
    new_val = (extra_params or {}).get("cacheRetention")
    if new_val in ("none", "short", "long"):
        return new_val  # type: ignore[return-value]
    if google or _is_anthropic_family(provider, model_api, model_id):
        return "short"
    return None