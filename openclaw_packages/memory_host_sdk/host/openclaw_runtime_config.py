from __future__ import annotations

import os
from typing import Any, Optional

from .config_utils import (
    CANONICAL_ROOT_MEMORY_FILENAME,
    normalize_agent_id,
    parse_duration_ms,
    resolve_user_path,
)
from .error_utils import format_error_message
from .fs_utils import is_path_inside
from .string_utils import normalize_lowercase_string_or_empty, normalize_optional_string


def parse_non_negative_byte_size(value: Optional[float]) -> int:
    if not isinstance(value, (int, float)) or value < 0:
        return 0
    return max(0, int(value))


def resolve_state_dir(env: Optional[dict] = None) -> str:
    env = env or os.environ
    override = (env.get("OPENCLAW_STATE_DIR") or "").strip()
    if override:
        return resolve_user_path(override)
    home = os.path.expanduser("~")
    new_dir = os.path.join(home, ".openclaw")
    if env.get("OPENCLAW_TEST_FAST") == "1" or os.path.exists(new_dir):
        return new_dir
    legacy = os.path.join(home, ".clawdbot")
    if os.path.exists(legacy):
        return legacy
    return new_dir


def resolve_session_transcripts_dir_for_agent(agent_id: str) -> str:
    state_dir = resolve_state_dir()
    return os.path.join(state_dir, "agents", normalize_agent_id(agent_id), "sessions")


def has_configured_secret_input(value: object) -> bool:
    from .secret_input_utils import has_configured_secret_input as _has
    return _has(value)


def normalize_resolved_secret_input_string(value: object, path: str) -> Optional[str]:
    from .secret_input_utils import normalize_resolved_secret_input_string as _normalize
    return _normalize(value, path)


def get_runtime_config() -> dict:
    return {}


def load_config() -> dict:
    return {}
