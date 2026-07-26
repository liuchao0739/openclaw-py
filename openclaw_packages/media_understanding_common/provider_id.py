"""Provider id normalization for media-understanding config and execution."""

from __future__ import annotations


def _normalize_provider_id(provider: str) -> str:
    return provider.strip().lower()


def normalize_media_provider_id(id: str) -> str:
    """Normalize provider aliases to canonical config provider ids."""
    normalized = _normalize_provider_id(id)
    if normalized == "gemini":
        return "google"
    if normalized == "minimax-cn":
        return "minimax"
    if normalized == "minimax-portal-cn":
        return "minimax-portal"
    return normalized


def normalize_media_execution_provider_id(id: str) -> str:
    """Normalize provider ids while preserving execution-specific regional aliases."""
    normalized = _normalize_provider_id(id)
    if normalized in ("minimax-cn", "minimax-portal-cn"):
        return normalized
    return normalize_media_provider_id(normalized)
