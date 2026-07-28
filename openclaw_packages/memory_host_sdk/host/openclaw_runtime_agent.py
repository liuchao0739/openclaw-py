from __future__ import annotations

from typing import Any, Optional

from .config_utils import (
    DEFAULT_AGENT_ID,
    parse_duration_ms,
    normalize_agent_id,
)


def resolve_cron_style_now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


DEFAULT_AGENT_COMPACTION_RESERVE_TOKENS_FLOOR = 0


def resolve_agent_context_limits(cfg: Optional[dict], agent_id: Optional[str] = None) -> Optional[dict]:
    defaults = (cfg or {}).get("agents", {}).get("defaults", {}).get("contextLimits")
    if not cfg or not agent_id:
        return defaults
    agents = cfg.get("agents", {}).get("list", [])
    if not isinstance(agents, list):
        return defaults
    for entry in agents:
        if entry and normalize_agent_id(entry.get("id")) == normalize_agent_id(agent_id):
            return entry.get("contextLimits") or defaults
    return defaults


def resolve_agent_dir(cfg: dict, agent_id: str) -> str:
    return resolve_agent_workspace_dir(cfg, agent_id)


def resolve_agent_workspace_dir(cfg: dict, agent_id: str, env: Optional[dict] = None) -> str:
    import os
    from .config_utils import normalize_agent_id, resolve_state_dir, resolve_user_path

    agent_id_normalized = normalize_agent_id(agent_id)
    agents = cfg.get("agents", {}).get("list", [])
    if not isinstance(agents, list):
        agents = []

    configured = None
    for entry in agents:
        if entry and normalize_agent_id(entry.get("id")) == agent_id_normalized:
            configured = (entry.get("workspace") or "").strip()
            break

    if configured:
        return resolve_user_path(configured)

    fallback = cfg.get("agents", {}).get("defaults", {}).get("workspace", "").strip()
    default_id = resolve_default_agent_id(cfg)
    if agent_id_normalized == default_id:
        if fallback:
            return resolve_user_path(fallback)
        home = os.path.expanduser("~")
        return os.path.join(home, ".openclaw", "workspace")

    if fallback:
        return os.path.join(resolve_user_path(fallback), agent_id_normalized)

    state_dir = resolve_state_dir()
    return os.path.join(state_dir, f"workspace-{agent_id_normalized}")


def resolve_default_agent_id(cfg: dict) -> str:
    agents = cfg.get("agents", {}).get("list", [])
    if not isinstance(agents, list) or not agents:
        return DEFAULT_AGENT_ID
    for agent in agents:
        if agent and agent.get("default"):
            return normalize_agent_id(agent.get("id") or DEFAULT_AGENT_ID)
    first = agents[0] if agents else None
    return normalize_agent_id((first or {}).get("id") or DEFAULT_AGENT_ID)


def resolve_session_agent_id(cfg: dict, session_key: str) -> str:
    return resolve_default_agent_id(cfg)


def resolve_memory_search_config(cfg: dict, agent_id: str) -> Optional[dict]:
    defaults = cfg.get("agents", {}).get("defaults", {}).get("memorySearch")
    overrides = None
    agents = cfg.get("agents", {}).get("list", [])
    if isinstance(agents, list):
        for entry in agents:
            if entry and normalize_agent_id(entry.get("id")) == normalize_agent_id(agent_id):
                overrides = entry.get("memorySearch")
                break

    enabled = (overrides or {}).get("enabled", (defaults or {}).get("enabled", True))
    if not enabled:
        return None

    raw_paths = []
    if defaults and defaults.get("extraPaths"):
        raw_paths.extend(defaults["extraPaths"])
    if overrides and overrides.get("extraPaths"):
        raw_paths.extend(overrides["extraPaths"])

    from .string_utils import normalize_string_entries, unique_strings
    return {
        "enabled": enabled,
        "extraPaths": unique_strings(normalize_string_entries(raw_paths)),
    }


def as_tool_params_record(params: dict) -> dict:
    return dict(params)


def jsonResult(result: object) -> dict:
    return {"result": result}


def read_number_param(params: dict, name: str, default: Optional[float] = None) -> Optional[float]:
    value = params.get(name)
    if isinstance(value, (int, float)):
        return float(value)
    return default


def read_string_param(params: dict, name: str, default: Optional[str] = None) -> Optional[str]:
    value = params.get(name)
    if isinstance(value, str):
        return value
    return default


def parse_agent_session_key(session_key: str) -> dict:
    parts = session_key.split(":")
    return {
        "sessionKey": session_key,
        "parts": parts,
    }
