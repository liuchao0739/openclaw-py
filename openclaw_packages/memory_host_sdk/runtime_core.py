from __future__ import annotations

from typing import Any, Dict, Optional

from .host.config_utils import (
    DEFAULT_AGENT_ID,
    normalize_agent_id,
    parse_duration_ms,
    resolve_default_agent_id,
    resolve_state_dir,
    resolve_user_path,
)
from .host.error_utils import format_error_message
from .host.string_utils import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
    unique_strings,
)


def get_runtime_config() -> dict:
    return {}


def load_config() -> dict:
    return {}


def resolve_state_dir(env: Optional[dict] = None) -> str:
    return resolve_state_dir(env)


def resolve_default_agent_id(cfg: dict) -> str:
    return resolve_default_agent_id(cfg)


def normalize_agent_id(agent_id: str) -> str:
    return normalize_agent_id(agent_id)


def parse_duration_ms(value: str, opts: Optional[dict] = None) -> int:
    return parse_duration_ms(value, opts)
