from __future__ import annotations

from typing import Any, Dict, List, Optional


def require_api_key(api_key: Optional[str], provider: str) -> str:
    if not api_key:
        raise RuntimeError(f"API key is required for provider: {provider}")
    return api_key


def resolve_api_key_for_provider(
    provider: str,
    cfg: Dict[str, Any],
    agent_dir: Optional[str] = None,
) -> Optional[str]:
    config = cfg or {}
    providers = ((config.get("models") or {}).get("providers") or {})
    provider_cfg = providers.get(provider) or {}
    return provider_cfg.get("apiKey")
