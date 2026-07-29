"""Diagnostic stability bundle helpers collect stable diagnostic data.

Mirrors src/logging/diagnostic-stability-bundle.ts.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

from openclaw.logging.diagnostic_stability import (
    MAX_DIAGNOSTIC_STABILITY_LIMIT,
    get_diagnostic_stability_snapshot,
)
from openclaw.logging.redact import redact_sensitive_text

DIAGNOSTIC_STABILITY_BUNDLE_VERSION = 1
DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_LIMIT = MAX_DIAGNOSTIC_STABILITY_LIMIT
DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_RETENTION = 20
MAX_DIAGNOSTIC_STABILITY_BUNDLE_BYTES = 5 * 1024 * 1024

SAFE_REASON_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$", re.UNICODE)
BUNDLE_PREFIX = "openclaw-stability-"
BUNDLE_SUFFIX = ".json"
REDACTED_HOSTNAME = "<redacted-hostname>"
MAX_SAFE_ERROR_MESSAGE_LENGTH = 500
MAX_SESSION_FILE_RESULTS = 20
MAX_SESSION_SCAN_AGENTS = 100
MAX_SESSION_SCAN_FILES = 5000

_fatal_hook_unsubscribe: Any = None


def _resolve_state_dir(env: dict[str, str] | None = None) -> str:
    e = env or os.environ
    state_dir = e.get("OPENCLAW_STATE_DIR")
    if state_dir:
        return state_dir
    return os.path.expanduser("~/.openclaw")


def _normalize_reason(reason: str) -> str:
    return reason if SAFE_REASON_CODE.match(reason) else "unknown"


def _format_bundle_timestamp(now: datetime) -> str:
    return now.isoformat().replace(":", "-").replace(".", "-")


def _read_error_code(error: Any) -> str | None:
    if not error or not isinstance(error, dict):
        return None
    code = error.get("code")
    if isinstance(code, str) and SAFE_REASON_CODE.match(code):
        return code
    if isinstance(code, (int, float)):
        return str(code)
    return None


def _read_error_name(error: Any) -> str | None:
    if not error or not isinstance(error, dict):
        return None
    name = error.get("name")
    if isinstance(name, str) and SAFE_REASON_CODE.match(name):
        return name
    return None


def _read_error_message(error: Any) -> str | None:
    if not error or not isinstance(error, dict):
        return None
    message = error.get("message")
    if not isinstance(message, str):
        return None
    sanitized = redact_sensitive_text(message, {"mode": "tools"})
    sanitized = " ".join(sanitized.split()).strip()
    if not sanitized:
        return None
    if len(sanitized) > MAX_SAFE_ERROR_MESSAGE_LENGTH:
        return sanitized[:MAX_SAFE_ERROR_MESSAGE_LENGTH] + "..."
    return sanitized


def _read_safe_error_metadata(error: Any) -> dict[str, Any] | None:
    name = _read_error_name(error)
    code = _read_error_code(error)
    message = _read_error_message(error)
    if not name and not code and not message:
        return None
    result: dict[str, Any] = {}
    if name:
        result["name"] = name
    if code:
        result["code"] = code
    if message:
        result["message"] = message
    return result


def resolve_diagnostic_stability_bundle_dir(
    options: dict[str, Any] | None = None,
) -> str:
    opts = options or {}
    return os.path.join(
        opts.get("stateDir") or _resolve_state_dir(opts.get("env")),
        "logs",
        "stability",
    )


def _build_bundle_path(dir_path: str, now: datetime, reason: str) -> str:
    return os.path.join(
        dir_path,
        f"{BUNDLE_PREFIX}{_format_bundle_timestamp(now)}-{os.getpid()}-{_normalize_reason(reason)}{BUNDLE_SUFFIX}",
    )


def _is_bundle_file(name: str) -> bool:
    return name.startswith(BUNDLE_PREFIX) and name.endswith(BUNDLE_SUFFIX)


def _is_missing_file_error(error: Any) -> bool:
    if isinstance(error, OSError) and error.errno == 2:
        return True
    if isinstance(error, dict) and error.get("code") == "ENOENT":
        return True
    return False


def _sanitize_session_evidence_path(relative_path: str) -> str:
    parts = relative_path.split("/")
    if len(parts) == 4 and parts[0] == "agents" and parts[2] == "sessions":
        return f"agents/<agent>/sessions/{_sanitize_session_evidence_file_name(parts[3])}"
    if len(parts) == 2 and parts[0] == "sessions":
        return f"sessions/{_sanitize_session_evidence_file_name(parts[1])}"
    return redact_sensitive_text(relative_path, {"mode": "tools"})


def _sanitize_session_evidence_file_name(file_name: str) -> str:
    if file_name == "sessions.json":
        return "sessions.json"
    if file_name.endswith(".jsonl"):
        return "<session>.jsonl"
    if file_name.endswith(".json"):
        return "<session>.json"
    return "<session>"


def _push_session_file_summary(
    results: list[dict[str, Any]],
    state_dir: str,
    file_path: str,
    relative_path_override: str | None = None,
) -> None:
    try:
        stat = os.stat(file_path)
        if not stat.st_size >= 0:
            return
        relative_path = relative_path_override or os.path.relpath(file_path, state_dir)
        relative_path = relative_path.replace("\\", "/")
        if relative_path.startswith("../") or os.path.isabs(relative_path):
            return
        results.append({
            "relativePath": _sanitize_session_evidence_path(relative_path),
            "sizeBytes": stat.st_size,
            "mtimeMs": int(stat.st_mtime * 1000),
        })
    except OSError:
        pass


def _collect_top_session_files(
    state_dir: str,
    session_store_paths: list[str] | None = None,
) -> list[dict[str, Any]] | None:
    results: list[dict[str, Any]] = []
    seen_dirs: set[str] = set()
    scanned = {"count": 0}
    try:
        _push_session_file_summary(results, state_dir, os.path.join(state_dir, "sessions.json"))
        agents_dir = os.path.join(state_dir, "agents")
        try:
            agent_entries = sorted(os.listdir(agents_dir))[:MAX_SESSION_SCAN_AGENTS]
        except OSError:
            agent_entries = []
        for agent_name in agent_entries:
            if scanned["count"] >= MAX_SESSION_SCAN_FILES:
                break
            sessions_dir = os.path.join(agents_dir, agent_name, "sessions")
            resolved = os.path.abspath(sessions_dir)
            if resolved in seen_dirs:
                continue
            seen_dirs.add(resolved)
            try:
                session_entries = os.listdir(sessions_dir)
            except OSError:
                continue
            for entry_name in session_entries:
                scanned["count"] += 1
                if scanned["count"] >= MAX_SESSION_SCAN_FILES:
                    break
                if not entry_name.endswith((".jsonl", ".json")):
                    continue
                _push_session_file_summary(
                    results,
                    state_dir,
                    os.path.join(sessions_dir, entry_name),
                    f"agents/{agent_name}/sessions/{entry_name}",
                )
        for store_path in session_store_paths or []:
            if scanned["count"] >= MAX_SESSION_SCAN_FILES:
                break
            sessions_dir = os.path.dirname(os.path.abspath(store_path))
            resolved = os.path.abspath(sessions_dir)
            if resolved in seen_dirs:
                continue
            seen_dirs.add(resolved)
            try:
                session_entries = os.listdir(sessions_dir)
            except OSError:
                continue
            for entry_name in session_entries:
                scanned["count"] += 1
                if scanned["count"] >= MAX_SESSION_SCAN_FILES:
                    break
                if not entry_name.endswith((".jsonl", ".json")):
                    continue
                _push_session_file_summary(
                    results,
                    state_dir,
                    os.path.join(sessions_dir, entry_name),
                    f"sessions/{entry_name}",
                )
    except OSError:
        pass
    top = sorted(results, key=lambda r: (-r["sizeBytes"], r["relativePath"]))[:MAX_SESSION_FILE_RESULTS]
    return top if top else None


def _build_memory_pressure_evidence(options: dict[str, Any]) -> dict[str, Any]:
    state_dir = options.get("stateDir") or _resolve_state_dir(options.get("env"))
    pressure = options["pressure"]
    top_session_files = _collect_top_session_files(state_dir, options.get("sessionStorePaths"))
    evidence: dict[str, Any] = {
        "memoryPressure": {
            "level": pressure.get("level"),
            "reason": pressure.get("reason"),
            "memory": pressure.get("memory"),
        }
    }
    mp = evidence["memoryPressure"]
    if pressure.get("thresholdBytes") is not None:
        mp["thresholdBytes"] = pressure["thresholdBytes"]
    if pressure.get("rssGrowthBytes") is not None:
        mp["rssGrowthBytes"] = pressure["rssGrowthBytes"]
    if pressure.get("windowMs") is not None:
        mp["windowMs"] = pressure["windowMs"]
    if top_session_files:
        mp["topSessionFiles"] = top_session_files
    return evidence


def list_diagnostic_stability_bundle_files_sync(
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    dir_path = resolve_diagnostic_stability_bundle_dir(options)
    try:
        entries = os.listdir(dir_path)
    except OSError as error:
        if _is_missing_file_error(error):
            return []
        raise
    result = []
    for name in entries:
        if not _is_bundle_file(name):
            continue
        file_path = os.path.join(dir_path, name)
        try:
            stat = os.stat(file_path)
            result.append({"path": file_path, "mtimeMs": int(stat.st_mtime * 1000)})
        except OSError:
            pass
    result.sort(key=lambda r: (-r["mtimeMs"], r["path"]))
    return result


def read_diagnostic_stability_bundle_file_sync(
    file_path: str,
) -> dict[str, Any]:
    try:
        stat = os.stat(file_path)
        if stat.st_size > MAX_DIAGNOSTIC_STABILITY_BUNDLE_BYTES:
            raise ValueError(
                f"Stability bundle is too large: {stat.st_size} bytes exceeds {MAX_DIAGNOSTIC_STABILITY_BUNDLE_BYTES}"
            )
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
        bundle = json.loads(raw)
        return {"status": "found", "path": file_path, "mtimeMs": int(stat.st_mtime * 1000), "bundle": bundle}
    except Exception as error:
        return {"status": "failed", "path": file_path, "error": error}


def read_latest_diagnostic_stability_bundle_sync(
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        files = list_diagnostic_stability_bundle_files_sync(options)
        if not files:
            return {"status": "missing", "dir": resolve_diagnostic_stability_bundle_dir(options)}
        return read_diagnostic_stability_bundle_file_sync(files[0]["path"])
    except Exception as error:
        return {"status": "failed", "error": error}


def _prune_old_bundles(dir_path: str, retention: int) -> None:
    if not isinstance(retention, (int, float)) or retention < 1:
        return
    try:
        entries = []
        for name in os.listdir(dir_path):
            if not _is_bundle_file(name):
                continue
            file_path = os.path.join(dir_path, name)
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                mtime = 0
            entries.append((file_path, int(mtime * 1000)))
        entries.sort(key=lambda r: (-r[1], r[0]))
        for file_path, _ in entries[retention:]:
            try:
                os.unlink(file_path)
            except OSError:
                pass
    except OSError:
        pass


def _replace_file_atomic(file_path: str, content: str) -> None:
    dir_path = os.path.dirname(file_path)
    os.makedirs(dir_path, exist_ok=True)
    temp_path = file_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(temp_path, file_path)


def write_diagnostic_stability_bundle_sync(
    options: dict[str, Any],
) -> dict[str, Any]:
    try:
        now = options.get("now") or datetime.now(timezone.utc)
        snapshot = get_diagnostic_stability_snapshot({
            "limit": options.get("limit") or DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_LIMIT,
        })
        if not options.get("includeEmpty") and snapshot["count"] == 0:
            return {"status": "skipped", "reason": "empty"}
        reason = _normalize_reason(options["reason"])
        error = _read_safe_error_metadata(options.get("error")) if options.get("error") else None
        bundle: dict[str, Any] = {
            "version": DIAGNOSTIC_STABILITY_BUNDLE_VERSION,
            "generatedAt": now.isoformat() if isinstance(now, datetime) else str(now),
            "reason": reason,
            "process": {
                "pid": os.getpid(),
                "platform": sys.platform,
                "arch": platform.machine(),
                "node": platform.python_version(),
                "uptimeMs": int(time.time() * 1000),
            },
            "host": {"hostname": REDACTED_HOSTNAME},
            "snapshot": snapshot,
        }
        if error:
            bundle["error"] = error
        if options.get("evidence"):
            bundle["evidence"] = options["evidence"]
        dir_path = resolve_diagnostic_stability_bundle_dir(options)
        file_path = _build_bundle_path(dir_path, now if isinstance(now, datetime) else datetime.now(timezone.utc), reason)
        _replace_file_atomic(file_path, json.dumps(bundle, indent=2) + "\n")
        _prune_old_bundles(dir_path, options.get("retention") or DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_RETENTION)
        return {"status": "written", "path": file_path, "bundle": bundle}
    except Exception as error:
        return {"status": "failed", "error": error}


def write_diagnostic_memory_pressure_bundle_sync(
    options: dict[str, Any],
) -> dict[str, Any]:
    return write_diagnostic_stability_bundle_sync({
        **options,
        "reason": "diagnostic.memory.pressure.critical",
        "includeEmpty": True,
        "evidence": _build_memory_pressure_evidence(options),
    })


def write_diagnostic_stability_bundle_for_failure_sync(
    reason: str,
    error: Any = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    opts = options or {}
    result = write_diagnostic_stability_bundle_sync({
        **opts,
        "reason": reason,
        "error": error,
        "includeEmpty": True,
    })
    if result["status"] == "written":
        return {"status": "written", "path": result["path"], "message": f"wrote stability bundle: {result['path']}"}
    if result["status"] == "failed":
        return {"status": "failed", "error": result["error"], "message": f"failed to write stability bundle: {result['error']}"}
    return result


def install_diagnostic_stability_fatal_hook(
    options: dict[str, Any] | None = None,
) -> None:
    global _fatal_hook_unsubscribe
    if _fatal_hook_unsubscribe:
        return
    try:
        from openclaw.infra.fatal_error_hooks import register_fatal_error_hook
        def hook(params: dict[str, Any]) -> str | None:
            result = write_diagnostic_stability_bundle_for_failure_sync(
                params.get("reason", "unknown"),
                params.get("error"),
                options or {},
            )
            return result.get("message")
        _fatal_hook_unsubscribe = register_fatal_error_hook(hook)
    except Exception:
        pass


def uninstall_diagnostic_stability_fatal_hook() -> None:
    global _fatal_hook_unsubscribe
    if _fatal_hook_unsubscribe:
        try:
            _fatal_hook_unsubscribe()
        except Exception:
            pass
    _fatal_hook_unsubscribe = None


def reset_diagnostic_stability_bundle_for_test() -> None:
    uninstall_diagnostic_stability_fatal_hook()


__all__ = [
    "DIAGNOSTIC_STABILITY_BUNDLE_VERSION",
    "DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_LIMIT",
    "DEFAULT_DIAGNOSTIC_STABILITY_BUNDLE_RETENTION",
    "MAX_DIAGNOSTIC_STABILITY_BUNDLE_BYTES",
    "resolve_diagnostic_stability_bundle_dir",
    "list_diagnostic_stability_bundle_files_sync",
    "read_diagnostic_stability_bundle_file_sync",
    "read_latest_diagnostic_stability_bundle_sync",
    "write_diagnostic_stability_bundle_sync",
    "write_diagnostic_memory_pressure_bundle_sync",
    "write_diagnostic_stability_bundle_for_failure_sync",
    "install_diagnostic_stability_fatal_hook",
    "uninstall_diagnostic_stability_fatal_hook",
    "reset_diagnostic_stability_bundle_for_test",
]
