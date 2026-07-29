"""Logger implementation writes structured log output with redaction and transports.

Mirrors src/logging/logger.ts.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from openclaw.logging.config import read_logging_config, should_skip_mutating_logging_config_read
from openclaw.logging.env_log_level import resolve_env_log_level_override
from openclaw.logging.levels import LogLevel, level_to_min_level, normalize_log_level
from openclaw.logging.log_file_shared import can_use_node_fs, format_local_date, LOG_PREFIX, LOG_SUFFIX
from openclaw.logging.log_file_path import resolve_configured_log_file_path
from openclaw.logging.redact import redact_sensitive_text
from openclaw.logging.state import logging_state

DEFAULT_LOG_DIR = "/tmp/openclaw"
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "openclaw.log")
MAX_LOG_AGE_MS = 24 * 60 * 60 * 1000
DEFAULT_MAX_LOG_FILE_BYTES = 100 * 1024 * 1024
MAX_ROTATED_LOG_FILES = 5


class Logger:
    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self._settings = settings or {}
        self._level = self._settings.get("level", "info")
        self._file = self._settings.get("file", DEFAULT_LOG_FILE)
        self._max_file_bytes = self._settings.get("maxFileBytes", DEFAULT_MAX_LOG_FILE_BYTES)
        self._file_handle: Any = None

    def _is_level_enabled(self, level: LogLevel) -> bool:
        if level == "silent":
            return False
        return level_to_min_level(level) >= level_to_min_level(self._level)

    def _write(self, level: LogLevel, message: str) -> None:
        if not self._is_level_enabled(level):
            return
        redacted = redact_sensitive_text(message)
        try:
            os.makedirs(os.path.dirname(self._file), exist_ok=True)
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(f"{redacted}\n")
        except OSError:
            pass

    def trace(self, message: str) -> None:
        self._write("trace", message)

    def debug(self, message: str) -> None:
        self._write("debug", message)

    def info(self, message: str) -> None:
        self._write("info", message)

    def warn(self, message: str) -> None:
        self._write("warn", message)

    def error(self, message: str) -> None:
        self._write("error", message)

    def fatal(self, message: str) -> None:
        self._write("fatal", message)


def _resolve_logger_settings() -> dict[str, Any]:
    env_level = resolve_env_log_level_override()
    cfg = logging_state.override_settings or read_logging_config()
    level = env_level or normalize_log_level(cfg.get("level") if cfg else None, "info")
    file_path = resolve_configured_log_file_path()
    max_file_bytes = DEFAULT_MAX_LOG_FILE_BYTES
    if cfg and isinstance(cfg.get("maxFileBytes"), (int, float)):
        max_file_bytes = int(cfg["maxFileBytes"])
    return {"level": level, "file": file_path, "maxFileBytes": max_file_bytes}


def get_logger() -> Logger:
    if logging_state.cached_logger is None:
        settings = _resolve_logger_settings()
        logging_state.cached_logger = Logger(settings)
        logging_state.cached_settings = settings
    return logging_state.cached_logger


def get_resolved_logger_settings() -> dict[str, Any]:
    if logging_state.cached_settings is None:
        get_logger()
    return logging_state.cached_settings


def get_child_logger(params: dict[str, Any]) -> Logger:
    return get_logger()


def is_file_log_level_enabled(level: LogLevel) -> bool:
    logger = get_logger()
    return logger._is_level_enabled(level)


def log_debug(message: str) -> None:
    get_logger().debug(message)


def log_info(message: str) -> None:
    get_logger().info(message)


def log_warn(message: str) -> None:
    get_logger().warn(message)


def log_error(message: str) -> None:
    get_logger().error(message)


def set_logger_config_loader_for_tests(loader: Any = None) -> None:
    logging_state.cached_logger = None
    logging_state.cached_settings = None


__all__ = [
    "Logger",
    "DEFAULT_LOG_DIR",
    "DEFAULT_LOG_FILE",
    "get_logger",
    "get_resolved_logger_settings",
    "get_child_logger",
    "is_file_log_level_enabled",
    "log_debug",
    "log_info",
    "log_warn",
    "log_error",
    "set_logger_config_loader_for_tests",
]
