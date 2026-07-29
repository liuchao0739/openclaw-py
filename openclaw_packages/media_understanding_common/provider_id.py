def _normalize_provider_id(provider: str) -> str:
    return provider.strip().lower()


def normalize_media_provider_id(id: str) -> str:
    normalized = _normalize_provider_id(id)
    if normalized == "gemini":
        return "google"
    if normalized == "minimax-cn":
        return "minimax"
    if normalized == "minimax-portal-cn":
        return "minimax-portal"
    return normalized


def normalize_media_execution_provider_id(id: str) -> str:
    normalized = _normalize_provider_id(id)
    if normalized == "minimax-cn" or normalized == "minimax-portal-cn":
        return normalized
    return normalize_media_provider_id(normalized)
