"""Migration provider context and report-directory helpers."""

from __future__ import annotations

import os
import time
from typing import Any, Callable


def _timestamp_ms_to_iso_file_stamp(ms: int | None = None) -> str:
    """Convert a timestamp in ms to an ISO-like file-safe stamp."""
    t = time.gmtime((ms or int(time.time() * 1000)) / 1000.0)
    return time.strftime("%Y%m%dT%H%M%SZ", t)


def create_migration_logger(
    runtime: dict[str, Any] | None = None,
    json_output: bool = False,
) -> dict[str, Callable[[str], None]]:
    """Build a migration logger that keeps JSON stdout machine-readable."""
    rt = runtime or {}
    log_fn = rt.get("error") if json_output else rt.get("log", print)
    error_fn = rt.get("error", print)

    def _debug(message: str) -> None:
        if os.environ.get("OPENCLAW_VERBOSE") == "1":
            (log_fn or print)(message)

    def _info(message: str) -> None:
        (log_fn or print)(message)

    def _warn(message: str) -> None:
        (error_fn or print)(message)

    def _error(message: str) -> None:
        (error_fn or print)(message)

    return {"debug": _debug, "info": _info, "warn": _warn, "error": _error}


def build_migration_report_dir(
    provider_id: str,
    state_dir: str,
    now_ms: int | None = None,
) -> str:
    """Build the timestamped directory where a provider writes migration reports."""
    stamp = _timestamp_ms_to_iso_file_stamp(now_ms)
    return os.path.join(state_dir, "migration", provider_id, stamp)


def build_migration_context(
    source: str | None = None,
    include_secrets: bool = False,
    overwrite: bool = False,
    provider_options: dict[str, Any] | None = None,
    backup_path: str | None = None,
    config_override: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
    report_dir: str | None = None,
    json_output: bool = False,
) -> dict[str, Any]:
    """Build the provider-facing migration context from CLI options and runtime state."""
    config = config_override
    if config is None:
        try:
            from openclaw.config.config import get_runtime_config

            config = get_runtime_config()
        except Exception:
            config = {}

    state_dir = os.path.expanduser("~/.openclaw")
    try:
        from openclaw.config.paths import resolve_state_dir

        state_dir = resolve_state_dir()
    except Exception:
        pass

    return {
        "config": config,
        "stateDir": state_dir,
        "source": source,
        "includeSecrets": include_secrets,
        "overwrite": overwrite,
        "providerOptions": provider_options,
        "backupPath": backup_path,
        "reportDir": report_dir,
        "logger": create_migration_logger(runtime, json_output),
    }
