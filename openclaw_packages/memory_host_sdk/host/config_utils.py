from __future__ import annotations

import os
import re
from typing import Any, List, Optional

from .string_utils import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
    normalize_string_entries,
    unique_strings,
)

CHAT_TYPES = ("direct", "group", "channel")
MEMORY_BACKENDS = ("builtin", "qmd")
MEMORY_CITATIONS_MODES = ("auto", "on", "off")
MEMORY_QMD_SEARCH_MODES = ("query", "search", "vsearch")
MEMORY_QMD_STARTUP_MODES = ("off", "idle", "immediate")
SESSION_SEND_POLICY_ACTIONS = ("allow", "deny")

CANONICAL_ROOT_MEMORY_FILENAME = "MEMORY.md"

DEFAULT_AGENT_ID = "main"
VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
INVALID_CHARS_RE = re.compile(r"[^a-z0-9_-]+", re.IGNORECASE)
LEADING_DASH_RE = re.compile(r"^-+")
TRAILING_DASH_RE = re.compile(r"-+$")
LEGACY_STATE_DIRNAMES = [".clawdbot"]
NEW_STATE_DIRNAME = ".openclaw"

DURATION_MULTIPLIERS = {
    "ms": 1,
    "s": 1000,
    "m": 60_000,
    "h": 3_600_000,
    "d": 86_400_000,
}


def round_duration_ms(raw: str, value: float) -> int:
    rounded = round(value)
    if not (-(2**53) <= rounded <= 2**53):
        raise ValueError(f"invalid duration: {raw}")
    return rounded


def normalize_agent_id(value: Optional[str]) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_AGENT_ID
    normalized = normalize_lowercase_string_or_empty(trimmed)
    if VALID_ID_RE.match(trimmed):
        return normalized
    result = INVALID_CHARS_RE.sub("-", normalized)
    result = LEADING_DASH_RE.sub("", result)
    result = TRAILING_DASH_RE.sub("", result)
    return (result[:64] or DEFAULT_AGENT_ID)


def parse_duration_ms(raw: str, opts: Optional[dict] = None) -> int:
    trimmed = normalize_lowercase_string_or_empty(normalize_optional_string(raw) or "")
    if not trimmed:
        raise ValueError("invalid duration (empty)")
    default_unit = (opts or {}).get("defaultUnit", "ms")

    single = re.match(r"^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$", trimmed)
    if single:
        value = float(single.group(1))
        if value < 0:
            raise ValueError(f"invalid duration: {raw}")
        unit = single.group(2) or default_unit
        return round_duration_ms(raw, value * DURATION_MULTIPLIERS.get(unit, 1))

    total_ms = 0.0
    consumed = 0
    token_re = re.compile(r"(\d+(?:\.\d+)?)(ms|s|m|h|d)")
    for match in token_re.finditer(trimmed):
        full = match.group(0)
        value_raw = match.group(1)
        unit_raw = match.group(2)
        index = match.start()
        if not full or index != consumed:
            raise ValueError(f"invalid duration: {raw}")
        value = float(value_raw)
        multiplier = DURATION_MULTIPLIERS.get(unit_raw)
        if value < 0 or not multiplier:
            raise ValueError(f"invalid duration: {raw}")
        total_ms += value * multiplier
        consumed += len(full)
    if consumed != len(trimmed) or consumed == 0:
        raise ValueError(f"invalid duration: {raw}")
    return round_duration_ms(raw, total_ms)


def resolve_user_path(path: str) -> str:
    if path.startswith("~"):
        return os.path.expanduser(path)
    if os.path.isabs(path):
        return path
    return os.path.abspath(path)


def resolve_state_dir(env: Optional[dict] = None) -> str:
    env = env or os.environ
    override = (env.get("OPENCLAW_STATE_DIR") or "").strip()
    if override:
        return resolve_user_path(override)
    home = os.path.expanduser("~")
    new_dir = os.path.join(home, NEW_STATE_DIRNAME)
    if env.get("OPENCLAW_TEST_FAST") == "1" or os.path.exists(new_dir):
        return new_dir
    for legacy in LEGACY_STATE_DIRNAMES:
        legacy_path = os.path.join(home, legacy)
        if os.path.exists(legacy_path):
            return legacy_path
    return new_dir


def resolve_default_agent_id(cfg: dict) -> str:
    agents = cfg.get("agents", {}).get("list", [])
    if not isinstance(agents, list) or not agents:
        return DEFAULT_AGENT_ID
    for agent in agents:
        if agent and agent.get("default"):
            return normalize_agent_id(agent.get("id") or DEFAULT_AGENT_ID)
    first = agents[0] if agents else None
    return normalize_agent_id((first or {}).get("id") or DEFAULT_AGENT_ID)


def resolve_agent_workspace_dir(cfg: dict, agent_id: str) -> str:
    normalized = normalize_agent_id(agent_id)
    agents = cfg.get("agents", {}).get("list", [])
    if isinstance(agents, list):
        for entry in agents:
            if entry and normalize_agent_id(entry.get("id")) == normalized:
                configured = (entry.get("workspace") or "").strip()
                if configured:
                    return resolve_user_path(configured)

    fallback = cfg.get("agents", {}).get("defaults", {}).get("workspace", "").strip()
    default_id = resolve_default_agent_id(cfg)
    if normalized == default_id:
        if fallback:
            return resolve_user_path(fallback)
        home = os.path.expanduser("~")
        return os.path.join(home, ".openclaw", "workspace")

    if fallback:
        return os.path.join(resolve_user_path(fallback), normalized)

    state_dir = resolve_state_dir()
    return os.path.join(state_dir, f"workspace-{normalized}")
