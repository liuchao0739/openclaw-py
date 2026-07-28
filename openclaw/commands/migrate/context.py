from __future__ import annotations

from typing import Any


def build_migration_context(
    source: str | None = None,
    include_secrets: bool = False,
    overwrite: bool = False,
    provider_options: dict[str, Any] | None = None,
    backup_path: str | None = None,
    runtime: dict[str, Any] | None = None,
    json_output: bool = False,
) -> dict[str, Any]:
    rt = runtime or {}
    context: dict[str, Any] = {
        "source": source,
        "includeSecrets": include_secrets,
        "overwrite": overwrite,
        "providerOptions": provider_options or {},
        "backupPath": backup_path,
        "jsonOutput": json_output,
        "config": {},
    }

    if source:
        context["config"] = _load_source_config(source)

    return context


def _load_source_config(source: str) -> dict[str, Any]:
    import json
    import os

    source_path = os.path.expanduser(source)
    if os.path.exists(source_path):
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def create_migration_logger(
    runtime: dict[str, Any],
    json_output: bool = False,
) -> dict[str, Any]:
    log_fn = runtime.get("log")
    error_fn = runtime.get("error")

    def info(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    def debug(msg: str) -> None:
        if not json_output and log_fn:
            log_fn(msg)

    def error(msg: str) -> None:
        if error_fn:
            error_fn(msg)
        elif log_fn:
            log_fn(msg)

    return {"info": info, "debug": debug, "error": error}
