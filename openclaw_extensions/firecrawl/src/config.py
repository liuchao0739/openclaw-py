"""Firecrawl helper module supports config behavior."""

from __future__ import annotations

import math
import os
from typing import Any, Literal, TypedDict

from openclaw.config.secrets import coerce_secret_ref
from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_web_search import resolve_timeout_seconds
from openclaw.utils.normalize_secret_input import (
    normalize_optional_secret_input,
)

DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"
DEFAULT_FIRECRAWL_SEARCH_TIMEOUT_SECONDS = 30
DEFAULT_FIRECRAWL_SCRAPE_TIMEOUT_SECONDS = 60
DEFAULT_FIRECRAWL_MAX_AGE_MS = 172_800_000
FIRECRAWL_API_KEY_ENV_VAR = "FIRECRAWL_API_KEY"


class _ConfiguredSecretResolutionAvailable(TypedDict):
    status: Literal["available"]
    value: str


class _ConfiguredSecretResolutionMissing(TypedDict):
    status: Literal["missing"]


class _ConfiguredSecretResolutionBlocked(TypedDict):
    status: Literal["blocked"]


ConfiguredSecretResolution = (
    _ConfiguredSecretResolutionAvailable
    | _ConfiguredSecretResolutionMissing
    | _ConfiguredSecretResolutionBlocked
)


def _resolve_search_config(cfg: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cfg or not is_record(cfg.get("tools")):
        return None
    web = cfg["tools"].get("web")
    if not is_record(web):
        return None
    search = web.get("search")
    return dict(search) if is_record(search) else None


def _resolve_fetch_config(cfg: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cfg or not is_record(cfg.get("tools")):
        return None
    web = cfg["tools"].get("web")
    if not is_record(web):
        return None
    fetch = web.get("fetch")
    return dict(fetch) if is_record(fetch) else None


def _resolve_firecrawl_plugin_config(cfg: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cfg or not is_record(cfg.get("plugins")):
        return None
    entries = cfg["plugins"].get("entries")
    if not is_record(entries):
        return None
    entry = entries.get("firecrawl")
    if not is_record(entry):
        return None
    plugin_config = entry.get("config")
    return dict(plugin_config) if is_record(plugin_config) else None


def resolve_firecrawl_search_config(cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    plugin_config = _resolve_firecrawl_plugin_config(cfg)
    plugin_web_search = plugin_config.get("webSearch") if plugin_config else None
    if is_record(plugin_web_search) and not isinstance(plugin_web_search, list):
        return dict(plugin_web_search)
    search = _resolve_search_config(cfg)
    if not search:
        return None
    firecrawl = search.get("firecrawl")
    return dict(firecrawl) if is_record(firecrawl) else None


def _resolve_firecrawl_fetch_config(cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    plugin_config = _resolve_firecrawl_plugin_config(cfg)
    plugin_web_fetch = plugin_config.get("webFetch") if plugin_config else None
    if is_record(plugin_web_fetch) and not isinstance(plugin_web_fetch, list):
        return dict(plugin_web_fetch)
    fetch = _resolve_fetch_config(cfg)
    if not fetch:
        return None
    firecrawl = fetch.get("firecrawl")
    return dict(firecrawl) if is_record(firecrawl) else None


def _resolve_default_secret_provider_alias(cfg: dict[str, Any], source: str = "env") -> str:
    secrets = cfg.get("secrets")
    if is_record(secrets):
        defaults = secrets.get("defaults")
        if is_record(defaults):
            configured = defaults.get(source)
            if isinstance(configured, str) and configured.strip():
                return configured.strip()
    return "default"


def _can_resolve_env_secret_ref_in_read_only_path(
    *,
    cfg: dict[str, Any] | None,
    provider: str,
    ref_id: str,
) -> bool:
    provider_config = None
    if cfg and is_record(cfg.get("secrets")):
        providers = cfg["secrets"].get("providers")
        if is_record(providers):
            provider_config = providers.get(provider)
    if not provider_config:
        return provider == _resolve_default_secret_provider_alias(cfg or {}, "env")
    if provider_config.get("source") != "env":
        return False
    allowlist = provider_config.get("allowlist")
    return not isinstance(allowlist, list) or ref_id in allowlist


def _resolve_secret_input_string(
    *,
    value: Any,
    path: str,
    defaults: Any = None,
) -> dict[str, Any]:
    normalized = normalize_optional_secret_input(value)
    if normalized:
        return {"status": "available", "value": normalized, "ref": None}
    ref = coerce_secret_ref(value)
    if not ref:
        return {"status": "missing", "value": None, "ref": None}
    return {"status": "configured_unavailable", "value": None, "ref": ref}


def _resolve_configured_secret(
    value: Any,
    path: str,
    cfg: dict[str, Any] | None = None,
) -> ConfiguredSecretResolution:
    defaults = None
    if cfg and is_record(cfg.get("secrets")):
        defaults = cfg["secrets"].get("defaults")
    resolved = _resolve_secret_input_string(value=value, path=path, defaults=defaults)
    if resolved["status"] == "available":
        normalized = normalize_optional_secret_input(resolved["value"])
        return (
            {"status": "available", "value": normalized}
            if normalized
            else {"status": "missing"}
        )
    if resolved["status"] == "missing":
        return {"status": "missing"}
    ref = resolved["ref"]
    if ref is None or ref.get("source") != "env":
        return {"status": "blocked"}
    env_var_name = str(ref.get("id") or "").strip()
    if env_var_name != FIRECRAWL_API_KEY_ENV_VAR:
        return {"status": "blocked"}
    if not _can_resolve_env_secret_ref_in_read_only_path(
        cfg=cfg,
        provider=str(ref.get("provider") or ""),
        ref_id=env_var_name,
    ):
        return {"status": "blocked"}
    env_value = normalize_optional_secret_input(os.environ.get(env_var_name))
    return {"status": "available", "value": env_value} if env_value else {"status": "missing"}


def resolve_firecrawl_api_key(cfg: dict[str, Any] | None = None) -> str | None:
    plugin_config = _resolve_firecrawl_plugin_config(cfg)
    search = resolve_firecrawl_search_config(cfg)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    configured_candidates = [
        {
            "value": plugin_config.get("webFetch", {}).get("apiKey")
            if plugin_config and is_record(plugin_config.get("webFetch"))
            else None,
            "path": "plugins.entries.firecrawl.config.webFetch.apiKey",
        },
        {
            "value": search.get("apiKey") if search else None,
            "path": "plugins.entries.firecrawl.config.webSearch.apiKey",
        },
        {
            "value": search.get("apiKey") if search else None,
            "path": "tools.web.search.firecrawl.apiKey",
        },
        {
            "value": fetch.get("apiKey") if fetch else None,
            "path": "tools.web.fetch.firecrawl.apiKey",
        },
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
    return normalize_optional_secret_input(os.environ.get(FIRECRAWL_API_KEY_ENV_VAR))


def resolve_firecrawl_base_url(cfg: dict[str, Any] | None = None) -> str:
    search = resolve_firecrawl_search_config(cfg)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    configured = (
        (search.get("baseUrl").strip() if search and isinstance(search.get("baseUrl"), str) else "")
        or (
            fetch.get("baseUrl").strip() if fetch and isinstance(fetch.get("baseUrl"), str) else ""
        )
        or normalize_optional_secret_input(os.environ.get("FIRECRAWL_BASE_URL"))
        or ""
    )
    return configured or DEFAULT_FIRECRAWL_BASE_URL


def resolve_firecrawl_only_main_content(
    cfg: dict[str, Any] | None = None,
    override: bool | None = None,
) -> bool:
    if isinstance(override, bool):
        return override
    fetch = _resolve_firecrawl_fetch_config(cfg)
    if fetch and isinstance(fetch.get("onlyMainContent"), bool):
        return fetch["onlyMainContent"]
    return True


def resolve_firecrawl_max_age_ms(
    cfg: dict[str, Any] | None = None,
    override: float | None = None,
) -> int:
    if isinstance(override, (int, float)) and math.isfinite(override) and override >= 0:
        return int(override)
    fetch = _resolve_firecrawl_fetch_config(cfg)
    max_age_ms = fetch.get("maxAgeMs") if fetch else None
    if isinstance(max_age_ms, (int, float)) and math.isfinite(max_age_ms) and max_age_ms >= 0:
        return int(max_age_ms)
    return DEFAULT_FIRECRAWL_MAX_AGE_MS


def _resolve_positive_timeout_seconds(value: Any, fallback: int) -> int:
    parsed = (
        value
        if isinstance(value, (int, float)) and math.isfinite(value) and value > 0
        else fallback
    )
    return resolve_timeout_seconds(parsed, fallback)


def resolve_firecrawl_scrape_timeout_seconds(
    cfg: dict[str, Any] | None = None,
    override: float | None = None,
) -> int:
    fetch = _resolve_firecrawl_fetch_config(cfg)
    fetch_timeout = fetch.get("timeoutSeconds") if fetch else None
    return _resolve_positive_timeout_seconds(
        override,
        _resolve_positive_timeout_seconds(fetch_timeout, DEFAULT_FIRECRAWL_SCRAPE_TIMEOUT_SECONDS),
    )


def resolve_firecrawl_search_timeout_seconds(override: float | None = None) -> int:
    return _resolve_positive_timeout_seconds(override, DEFAULT_FIRECRAWL_SEARCH_TIMEOUT_SECONDS)
