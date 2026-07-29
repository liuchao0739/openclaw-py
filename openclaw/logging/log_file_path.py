"""Log file path helpers resolve log output paths for local runtime logs.

Mirrors src/logging/log-file-path.ts.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Any

from openclaw.logging.log_file_shared import (
    LOG_PREFIX,
    LOG_SUFFIX,
    can_use_node_fs,
    format_local_date,
)

POSIX_OPENCLAW_TMP_DIR = "/tmp/openclaw"


def resolve_preferred_openclaw_tmp_dir() -> str:
    return os.environ.get("OPENCLAW_TMP_DIR") or POSIX_OPENCLAW_TMP_DIR


def _resolve_default_rolling_log_file(date: datetime | None = None) -> str:
    date = date or datetime.now()
    log_dir = resolve_preferred_openclaw_tmp_dir() if can_use_node_fs() else POSIX_OPENCLAW_TMP_DIR
    return os.path.join(log_dir, f"{LOG_PREFIX}-{format_local_date(date)}{LOG_SUFFIX}")


def resolve_configured_log_file_path(config: Any = None) -> str:
    logging_config = getattr(config, "logging", None) if config else None
    if logging_config and isinstance(logging_config, dict):
        file_path = logging_config.get("file")
        if isinstance(file_path, str) and file_path:
            return file_path
    elif logging_config is not None:
        file_path = getattr(logging_config, "file", None)
        if isinstance(file_path, str) and file_path:
            return file_path
    return _resolve_default_rolling_log_file()


__all__ = [
    "POSIX_OPENCLAW_TMP_DIR",
    "resolve_preferred_openclaw_tmp_dir",
    "resolve_configured_log_file_path",
]
