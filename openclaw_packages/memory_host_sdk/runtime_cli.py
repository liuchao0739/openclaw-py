from __future__ import annotations

from typing import Any, Dict, List, Optional

from .host.config_utils import (
    DEFAULT_AGENT_ID,
    normalize_agent_id,
    parse_duration_ms,
    resolve_agent_workspace_dir,
    resolve_state_dir,
    resolve_user_path,
)
from .host.error_utils import format_error_message, redact_sensitive_text
from .host.string_utils import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
    unique_strings,
)


def format_error_message(err: object) -> str:
    return format_error_message(err)


def redact_sensitive_text(text: str) -> str:
    return redact_sensitive_text(text)


def get_runtime_config() -> dict:
    return {}


def load_config() -> dict:
    return {}


def resolve_state_dir(env: Optional[dict] = None) -> str:
    return resolve_state_dir(env)
