import os
from typing import Any, Optional

from .._sdk import (
    can_resolve_env_secret_ref_in_read_only_path,
    normalize_secret_input,
    resolve_positive_timeout_seconds,
    resolve_secret_input_string,
)

DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"
DEFAULT_FIRECRAWL_SEARCH_TIMEOUT_SECONDS = 30
DEFAULT_FIRECRAWL_SCRAPE_TIMEOUT_SECONDS = 60
DEFAULT_FIRECRAWL_MAX_AGE_MS = 172800000
FIRECRAWL_API_KEY_ENV_VAR = "FIRECRAWL_API_KEY"


def _resolve_search_config(cfg: Optional[dict]) -> Optional[dict]:
    if not cfg:
        return None
    search = cfg.get("tools", {}).get("web", {}).get("search")
    if not isinstance(search, dict):
        return None
    return search


def _resolve_fetch_config(cfg: Optional[dict]) -> Optional[dict]:
    if not cfg:
        return None
    fetch = cfg.get("tools", {}).get("web", {}).get("fetch")
    if not isinstance(fetch, dict):
        return None
    return fetch


def resolve_firecrawl_search_config(cfg: Optional[dict]) -> Optional[dict]:
    if not cfg:
        return None
    plugin_config = (cfg.get("plugins", {}).get("entries", {}).get("firecrawl", {}) or {}).get("config")
    plugin_web_search = plugin_config.get("webSearch") if isinstance(plugin_config, dict) else None
    if isinstance(plugin_web_search, dict):
        return plugin_web_search
    search = _resolve_search_config(cfg)
    if not isinstance(search, dict):
        return None
    firecrawl = search.get("firecrawl")
    if not isinstance(firecrawl, dict):
        return None
    return firecrawl


def _resolve_firecrawl_fetch_config(cfg: Optional[dict]) -> Optional[dict]:
    if not cfg:
        return None
    plugin_config = (cfg.get("plugins", {}).get("entries", {}).get("firecrawl", {}) or {}).get("config")
    plugin_web_fetch = plugin_config.get("webFetch") if isinstance(plugin_config, dict) else None
    if isinstance(plugin_web_fetch, dict):
        return plugin_web_fetch
    fetch = _resolve_fetch_config(cfg)
    if not isinstance(fetch, dict):
        return None
    firecrawl = fetch.get("firecrawl")
    if not isinstance(firecrawl, dict):
        return None
    return firecrawl


def _resolve_configured_secret(value: Any, path: str, cfg: Optional[dict]) -> dict:
    resolved = resolve_secret_input_string(value, path, cfg.get("secrets", {}).get("defaults") if cfg else None)
    if resolved["status"] == "available":
        normalized = normalize_secret_input(resolved["value"])
        if normalized:
            return {"status": "available", "value": normalized}
        return {"status": "missing"}
    if resolved["status"] == "missing":
        return {"status": "missing"}
    ref = resolved.get("ref", {})
    if ref.get("source") != "env":
        return {"status": "blocked"}
    env_var_name = str(ref.get("id", "")).strip()
    if env_var_name != FIRECRAWL_API_KEY_ENV_VAR:
        return {"status": "blocked"}
    if not can_resolve_env_secret_ref_in_read_only_path(cfg=cfg, provider=ref.get("provider"), id=env_var_name):
        return {"status": "blocked"}
    env_value = normalize_secret_input(os.environ.get(env_var_name))
    if env_value:
        return {"status": "available", "value": env_value}
    return {"status": "missing"}


def resolve_firecrawl_api_key(cfg: Optional[dict] = None) -> Optional[str]:
    plugin_config = (cfg.get("plugins", {}).get("entries", {}).get("firecrawl", {}) or {}).get("config") if cfg else None
    search = resolve_firecrawl_search_config(cfg)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    configured_candidates = [
        {"value": plugin_config.get("webFetch", {}).get("apiKey") if isinstance(plugin_config, dict) else None, "path": "plugins.entries.firecrawl.config.webFetch.apiKey"},
        {"value": search.get("apiKey") if search else None, "path": "plugins.entries.firecrawl.config.webSearch.apiKey"},
        {"value": search.get("apiKey") if search else None, "path": "tools.web.search.firecrawl.apiKey"},
        {"value": fetch.get("apiKey") if fetch else None, "path": "tools.web.fetch.firecrawl.apiKey"},
    ]
    blocked_configured_secret = False
    for candidate in configured_candidates:
        resolved = _resolve_configured_secret(candidate["value"], candidate["path"], cfg)
        if resolved["status"] == "available":
            return resolved["value"]
        if resolved["status"] == "blocked":
            blocked_configured_secret = True
    if blocked_configured_secret:
        return None
    return normalize_secret_input(os.environ.get(FIRECRAWL_API_KEY_ENV_VAR)) or None


def resolve_firecrawl_base_url(cfg: Optional[dict] = None) -> str:
    search = resolve_firecrawl_search_config(cfg)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    configured = ""
    if search and isinstance(search.get("baseUrl"), str):
        configured = search["baseUrl"].strip()
    if not configured and fetch and isinstance(fetch.get("baseUrl"), str):
        configured = fetch["baseUrl"].strip()
    if not configured:
        configured = normalize_secret_input(os.environ.get("FIRECRAWL_BASE_URL")) or ""
    return configured or DEFAULT_FIRECRAWL_BASE_URL


def resolve_firecrawl_only_main_content(cfg: Optional[dict] = None, override: Optional[bool] = None) -> bool:
    if isinstance(override, bool):
        return override
    fetch = _resolve_firecrawl_fetch_config(cfg)
    if fetch and isinstance(fetch.get("onlyMainContent"), bool):
        return fetch["onlyMainContent"]
    return True


def resolve_firecrawl_max_age_ms(cfg: Optional[dict] = None, override: Optional[int] = None) -> int:
    if isinstance(override, (int, float)) and override == override and override >= 0:
        return int(override)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    if fetch and isinstance(fetch.get("maxAgeMs"), (int, float)) and fetch["maxAgeMs"] == fetch["maxAgeMs"] and fetch["maxAgeMs"] >= 0:
        return int(fetch["maxAgeMs"])
    return DEFAULT_FIRECRAWL_MAX_AGE_MS


def resolve_firecrawl_scrape_timeout_seconds(cfg: Optional[dict] = None, override: Optional[int] = None) -> int:
    fetch = _resolve_firecrawl_fetch_config(cfg)
    return resolve_positive_timeout_seconds(
        override,
        resolve_positive_timeout_seconds(fetch.get("timeoutSeconds") if fetch else None, DEFAULT_FIRECRAWL_SCRAPE_TIMEOUT_SECONDS),
    )


def resolve_firecrawl_search_timeout_seconds(override: Optional[int] = None) -> int:
    return resolve_positive_timeout_seconds(override, DEFAULT_FIRECRAWL_SEARCH_TIMEOUT_SECONDS)
