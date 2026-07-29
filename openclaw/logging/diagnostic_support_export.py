"""Diagnostic support export helpers write support bundles to disk.

Mirrors src/logging/diagnostic-support-export.ts.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from typing import Any

from openclaw.logging.diagnostic_stability_bundle import (
    read_diagnostic_stability_bundle_file_sync,
    read_latest_diagnostic_stability_bundle_sync,
)
from openclaw.logging.diagnostic_support_bundle import (
    json_support_bundle_file,
    jsonl_support_bundle_file,
    support_bundle_contents,
    text_support_bundle_file,
    write_support_bundle_zip,
)
from openclaw.logging.diagnostic_support_log_redaction import sanitize_support_log_record
from openclaw.logging.diagnostic_support_redaction import (
    redact_path_for_support,
    redact_support_string,
    redact_text_for_support,
    sanitize_support_config_value,
    sanitize_support_snapshot_value,
)

DIAGNOSTIC_SUPPORT_EXPORT_VERSION = 1
DEFAULT_LOG_LIMIT = 5000
DEFAULT_LOG_MAX_BYTES = 1000000
SUPPORT_EXPORT_PREFIX = "openclaw-diagnostics-"
SUPPORT_EXPORT_SUFFIX = ".zip"


def _resolve_state_dir(env: dict[str, str] | None = None) -> str:
    e = env or os.environ
    return e.get("OPENCLAW_STATE_DIR") or os.path.expanduser("~/.openclaw")


def _resolve_version() -> str:
    try:
        from openclaw.version import VERSION
        return VERSION
    except Exception:
        return "unknown"


def _format_export_timestamp(now: datetime) -> str:
    return now.isoformat().replace(":", "-").replace(".", "-")


def _normalize_positive_integer(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 1:
        return fallback
    return parsed


def _safe_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        redacted = redact_text_for_support(value)
        if redacted == value and all(c.isalnum() or c in "_.:-" for c in value) and len(value) <= 120:
            return value
        return "<redacted>"
    return None


def _sorted_object_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return sorted(value.keys())
    return []


def _resolve_bonjour_env_override(env: dict[str, str]) -> str:
    raw = (env.get("OPENCLAW_DISABLE_BONJOUR") or "").strip().lower()
    if not raw:
        return "unset"
    if raw in ("1", "true", "yes", "on"):
        return "force-disabled"
    if raw in ("0", "false", "no", "off"):
        return "force-enabled"
    return "unrecognized"


def _sanitize_config_shape(parsed: Any, config_path: str, stat: os.stat_result, env: dict[str, str]) -> dict[str, Any]:
    root = parsed if isinstance(parsed, dict) else {}
    gateway = root.get("gateway") if isinstance(root.get("gateway"), dict) else None
    auth = gateway.get("auth") if gateway and isinstance(gateway.get("auth"), dict) else None
    discovery = root.get("discovery") if isinstance(root.get("discovery"), dict) else None
    mdns = discovery.get("mdns") if discovery and isinstance(discovery.get("mdns"), dict) else None
    channels = root.get("channels") if isinstance(root.get("channels"), dict) else None
    plugins = root.get("plugins") if isinstance(root.get("plugins"), dict) else None
    agents = root.get("agents") if isinstance(root.get("agents"), list) else None

    shape: dict[str, Any] = {
        "path": config_path,
        "exists": True,
        "parseOk": True,
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "topLevelKeys": _sorted_object_keys(root),
    }
    if gateway:
        shape["gateway"] = {
            "mode": _safe_scalar(gateway.get("mode")),
            "bind": _safe_scalar(gateway.get("bind")),
            "port": _safe_scalar(gateway.get("port")),
            "authMode": _safe_scalar(auth.get("mode") if auth else None),
            "tailscale": _safe_scalar(gateway.get("tailscale")),
        }
    bonjour_env_override = _resolve_bonjour_env_override(env)
    if mdns or bonjour_env_override != "unset":
        shape["discovery"] = {"mdnsMode": _safe_scalar(mdns.get("mode") if mdns else None), "bonjourEnvOverride": bonjour_env_override}
    if channels:
        shape["channels"] = {"count": len(channels), "ids": _sorted_object_keys(channels)}
    if plugins:
        shape["plugins"] = {"count": len(plugins), "ids": _sorted_object_keys(plugins)}
    if agents:
        shape["agents"] = {"count": len(agents)}
    return shape


def _config_shape_read_failure(params: dict[str, Any]) -> dict[str, Any]:
    shape: dict[str, Any] = {
        "path": params["configPath"],
        "exists": bool(params.get("stat")),
        "parseOk": False,
        "topLevelKeys": [],
    }
    stat = params.get("stat")
    if stat:
        shape["bytes"] = stat.st_size
        shape["mtime"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    if params.get("error"):
        shape["error"] = redact_support_string(params["error"], params["redaction"])
    return shape


def _is_missing_path_error(error: Any) -> bool:
    if isinstance(error, OSError) and error.errno in (2, 20):
        return True
    if isinstance(error, dict) and error.get("code") in ("ENOENT", "ENOTDIR"):
        return True
    return False


def _config_read_error_message(error: Any, stat: os.stat_result | None = None) -> str | None:
    if not stat and _is_missing_path_error(error):
        return None
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def _read_config_export(options: dict[str, Any]) -> dict[str, Any]:
    redacted_config_path = redact_path_for_support(options["configPath"], options)
    stat: os.stat_result | None = None
    try:
        stat = os.stat(options["configPath"])
        with open(options["configPath"], "r", encoding="utf-8") as f:
            content = f.read()
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as error:
            return {"shape": _config_shape_read_failure({"configPath": redacted_config_path, "redaction": options, "stat": stat, "error": str(error)})}
        return {
            "shape": _sanitize_config_shape(parsed, redacted_config_path, stat, options["env"]),
            "sanitized": sanitize_support_config_value(parsed, options),
        }
    except Exception as error:
        return {
            "shape": _config_shape_read_failure({
                "configPath": redacted_config_path,
                "redaction": options,
                "stat": stat,
                "error": _config_read_error_message(error, stat),
            })
        }


def _redact_error_for_support(error: Any, redaction: dict[str, Any]) -> str:
    message = str(error) if not isinstance(error, Exception) else str(error)
    return redact_support_string(message, redaction)


async def _collect_support_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    if not params.get("reader"):
        return {"summary": {"status": "skipped"}}
    try:
        data = await params["reader"]() if callable(params.get("reader")) else params["reader"]()
        return {
            "summary": {"status": "included", "path": params["path"]},
            "file": json_support_bundle_file(params["path"], {
                "status": "ok",
                "capturedAt": params["generatedAt"],
                "data": sanitize_support_snapshot_value(data, params["redaction"]),
            }),
        }
    except Exception as error:
        redacted_error = _redact_error_for_support(error, params["redaction"])
        return {
            "summary": {"status": "failed", "path": params["path"], "error": redacted_error},
            "file": json_support_bundle_file(params["path"], {
                "status": "failed",
                "capturedAt": params["generatedAt"],
                "error": redacted_error,
            }),
        }


def _read_stability_bundle(target: Any, state_dir: str) -> dict[str, Any]:
    if target is False:
        return {"status": "missing", "dir": "$OPENCLAW_STATE_DIR/logs/stability"}
    if target is None or target == "latest":
        return read_latest_diagnostic_stability_bundle_sync({"stateDir": state_dir})
    return read_diagnostic_stability_bundle_file_sync(target)


def _sanitize_log_tail(tail: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "included",
        "file": redact_path_for_support(tail.get("file"), options),
        "cursor": tail.get("cursor", 0),
        "size": tail.get("size", 0),
        "lineCount": len(tail.get("lines", [])),
        "truncated": tail.get("truncated", False),
        "reset": tail.get("reset", False),
        "lines": [sanitize_support_log_record(line, options) for line in tail.get("lines", [])],
    }


def _failed_log_tail(error: Any, redaction: dict[str, Any]) -> dict[str, Any]:
    redacted_error = _redact_error_for_support(error, redaction)
    return {
        "status": "failed",
        "file": "unavailable",
        "cursor": 0,
        "size": 0,
        "lineCount": 0,
        "truncated": False,
        "reset": False,
        "error": redacted_error,
        "lines": [{"omitted": "log-tail-read-failed", "error": redacted_error}],
    }


def _log_string(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _is_bonjour_log_record(record: dict[str, Any]) -> bool:
    source_fields = ["subsystem", "logger", "module", "pluginId", "component"]
    for field in source_fields:
        val = _log_string(record, field)
        if val and "bonjour" in val.lower():
            return True
    msg = _log_string(record, "msg")
    return msg is not None and msg.lower().startswith("bonjour:")


def _classify_bonjour_log_kind(normalized_msg: str) -> str:
    if "disabling" in normalized_msg:
        return "disabled"
    if "restarting" in normalized_msg:
        return "restarted"
    if "suppressing ciao" in normalized_msg:
        return "ciao_suppressed"
    if "conflict" in normalized_msg:
        return "conflict"
    if "watchdog" in normalized_msg:
        return "watchdog"
    return "other"


def _summarize_bonjour_logs(log_tail: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"count": 0, "warnings": 0, "flags": {"disabled": False, "restarted": False, "ciaoSuppressed": False}}
    for record in log_tail.get("lines", []):
        if not isinstance(record, dict) or not _is_bonjour_log_record(record):
            continue
        summary["count"] += 1
        level = (_log_string(record, "level") or "").lower()
        if level in ("warn", "error"):
            summary["warnings"] += 1
        msg = _log_string(record, "msg") or ""
        normalized_msg = msg.lower()
        summary["flags"]["disabled"] = summary["flags"]["disabled"] or "disabling" in normalized_msg
        summary["flags"]["restarted"] = summary["flags"]["restarted"] or "restarting" in normalized_msg
        summary["flags"]["ciaoSuppressed"] = summary["flags"]["ciaoSuppressed"] or "suppressing ciao" in normalized_msg
        last: dict[str, Any] = {"kind": _classify_bonjour_log_kind(normalized_msg)}
        time_val = _log_string(record, "time")
        if time_val:
            last["time"] = time_val
        level_val = _log_string(record, "level")
        if level_val:
            last["level"] = level_val
        summary["last"] = last
    return summary


async def _collect_support_log_tail(params: dict[str, Any]) -> dict[str, Any]:
    try:
        read_log_tail = params["readLogTail"]
        tail = await read_log_tail({"limit": params["limit"], "maxBytes": params["maxBytes"]})
        return _sanitize_log_tail(tail, params["redaction"])
    except Exception as error:
        return _failed_log_tail(error, params["redaction"])


def _describe_stability_for_diagnostics(stability: dict[str, Any], redaction: dict[str, Any]) -> dict[str, Any]:
    if stability.get("status") == "found":
        bundle = stability.get("bundle") or {}
        snapshot = bundle.get("snapshot") or {}
        return {
            "status": "found",
            "path": redact_path_for_support(stability.get("path"), redaction),
            "mtimeMs": stability.get("mtimeMs"),
            "eventCount": snapshot.get("count", 0),
            "reason": bundle.get("reason"),
            "generatedAt": bundle.get("generatedAt"),
        }
    if stability.get("status") == "missing":
        return {"status": "missing", "dir": redact_path_for_support(stability.get("dir"), redaction)}
    return {
        "status": "failed",
        "path": redact_path_for_support(stability.get("path"), redaction) if stability.get("path") else None,
        "error": _redact_error_for_support(stability.get("error"), redaction),
    }


def _render_summary(params: dict[str, Any]) -> str:
    stability_line = (
        f"included latest stability bundle ({params['stability'].get('bundle', {}).get('snapshot', {}).get('count', 0)} event(s))"
        if params["stability"].get("status") == "found"
        else f"no stability bundle included ({params['stability'].get('status')})"
    )
    config_line = (
        f"config shape included ({'parsed' if params['config'].get('parseOk') else 'parse failed'})"
        if params["config"].get("exists")
        else "config file not found"
    )
    log_tail_line = (
        f"sanitized log tail unavailable ({params['logTail'].get('error')})"
        if params["logTail"].get("status") == "failed"
        else f"sanitized log tail ({params['logTail'].get('lineCount', 0)} line(s), inspected {params['logTail'].get('size', 0)} byte(s), raw messages omitted)"
    )

    def snapshot_line(label: str, snapshot: dict[str, Any]) -> str:
        if snapshot.get("status") == "included":
            return f"{label} snapshot included ({snapshot.get('path')})"
        if snapshot.get("status") == "failed":
            return f"{label} snapshot failed ({snapshot.get('error')})"
        return f"{label} snapshot skipped"

    lines = [
        "# OpenClaw Diagnostics Export",
        "",
        "Attach this zip to the bug report. It is designed for maintainers to inspect without asking for raw logs first.",
        "",
        "## Generated",
        "",
        f"Generated: {params['generatedAt']}",
        f"OpenClaw: {_resolve_version()}",
        "",
        "## Contents",
        "",
        f"- {stability_line}",
        f"- {log_tail_line}",
        f"- {config_line}",
        f"- {snapshot_line('gateway status', params['status'])}",
        f"- {snapshot_line('gateway health', params['health'])}",
        "",
        "## Privacy",
        "",
        "- raw chat text, webhook bodies, tool outputs, tokens, cookies, and secrets are not included intentionally",
        "- log records keep operational summaries and safe metadata fields",
        "- status and health snapshots redact secret fields, payload-like fields, and account/message identifiers",
        "- config output keeps useful settings but redacts secrets, private identifiers, and prompt text",
    ]
    return "\n".join(lines)


def _default_output_path(options: dict[str, Any]) -> str:
    return os.path.join(
        options["stateDir"],
        "logs",
        "support",
        f"{SUPPORT_EXPORT_PREFIX}{_format_export_timestamp(options['now'])}-{os.getpid()}{SUPPORT_EXPORT_SUFFIX}",
    )


def _resolve_output_path(options: dict[str, Any]) -> str:
    raw = (options.get("outputPath") or "").strip()
    if not raw:
        return _default_output_path(options)
    if os.path.isabs(raw) or raw.startswith("~"):
        resolved = os.path.expanduser(raw)
    else:
        resolved = os.path.join(options["cwd"], raw)
    try:
        if os.path.isdir(resolved):
            return os.path.join(
                resolved,
                f"{SUPPORT_EXPORT_PREFIX}{_format_export_timestamp(options['now'])}-{os.getpid()}{SUPPORT_EXPORT_SUFFIX}",
            )
    except OSError:
        pass
    return resolved


def _read_configured_log_tail(params: dict[str, Any]) -> dict[str, Any]:
    try:
        from openclaw.logging.log_tail import read_configured_log_tail
        return read_configured_log_tail(params)
    except Exception:
        return {"file": "unavailable", "cursor": 0, "size": 0, "lines": [], "truncated": False, "reset": False}


async def build_diagnostic_support_export(options: dict[str, Any] | None = None) -> dict[str, Any]:
    opts = options or {}
    env = opts.get("env") or dict(os.environ)
    state_dir = opts.get("stateDir") or _resolve_state_dir(env)
    now = opts.get("now") or datetime.now(timezone.utc)
    generated_at = now.isoformat() if isinstance(now, datetime) else str(now)
    config_path = opts.get("configPath") or os.path.join(state_dir, "config.json")
    stability = _read_stability_bundle(opts.get("stabilityBundle"), state_dir)
    redaction = {"env": env, "stateDir": state_dir}
    log_tail = await _collect_support_log_tail({
        "readLogTail": opts.get("readLogTail") or _read_configured_log_tail,
        "limit": _normalize_positive_integer(opts.get("logLimit"), DEFAULT_LOG_LIMIT),
        "maxBytes": _normalize_positive_integer(opts.get("logMaxBytes"), DEFAULT_LOG_MAX_BYTES),
        "redaction": redaction,
    })
    config = _read_config_export({"configPath": config_path, "env": env, "stateDir": state_dir, **redaction})
    status_snapshot = await _collect_support_snapshot({"path": "status/gateway-status.json", "reader": opts.get("readStatusSnapshot"), "generatedAt": generated_at, "redaction": redaction})
    health_snapshot = await _collect_support_snapshot({"path": "health/gateway-health.json", "reader": opts.get("readHealthSnapshot"), "generatedAt": generated_at, "redaction": redaction})

    diagnostics = {
        "generatedAt": generated_at,
        "openclawVersion": _resolve_version(),
        "process": {"platform": sys.platform, "arch": platform.machine(), "node": platform.python_version(), "pid": os.getpid()},
        "stateDir": redact_path_for_support(state_dir, redaction),
        "config": config["shape"],
        "logs": {
            "file": log_tail.get("file"),
            "cursor": log_tail.get("cursor", 0),
            "size": log_tail.get("size", 0),
            "lineCount": log_tail.get("lineCount", 0),
            "truncated": log_tail.get("truncated", False),
            "reset": log_tail.get("reset", False),
        },
        "stability": _describe_stability_for_diagnostics(stability, redaction),
        "bonjour": _summarize_bonjour_logs(log_tail),
        "status": status_snapshot["summary"],
        "health": health_snapshot["summary"],
    }

    files = [
        json_support_bundle_file("diagnostics.json", diagnostics),
        json_support_bundle_file("config/shape.json", config["shape"]),
        json_support_bundle_file("config/sanitized.json", config.get("sanitized")),
        jsonl_support_bundle_file("logs/openclaw-sanitized.jsonl", [json.dumps(line) for line in log_tail.get("lines", [])]),
    ]
    for snapshot in (status_snapshot, health_snapshot):
        if snapshot.get("file"):
            files.append(snapshot["file"])
    if stability.get("status") == "found":
        files.append(json_support_bundle_file("stability/latest.json", stability["bundle"]))
    files.append(text_support_bundle_file("summary.md", _render_summary({
        "generatedAt": generated_at,
        "stability": stability,
        "logTail": log_tail,
        "config": config["shape"],
        "status": status_snapshot["summary"],
        "health": health_snapshot["summary"],
    })))

    manifest = {
        "version": DIAGNOSTIC_SUPPORT_EXPORT_VERSION,
        "generatedAt": generated_at,
        "openclawVersion": _resolve_version(),
        "platform": sys.platform,
        "arch": platform.machine(),
        "node": platform.python_version(),
        "stateDir": redact_path_for_support(state_dir, redaction),
        "contents": support_bundle_contents(files),
        "privacy": {
            "payloadFree": True,
            "rawLogsIncluded": False,
            "notes": [
                "Stability bundles are payload-free diagnostic snapshots.",
                "Logs keep operational summaries and safe metadata fields; payload-like fields are omitted.",
                "Status and health snapshots redact secrets, payload-like fields, and account/message identifiers.",
                "Config output includes useful settings with credentials, private identifiers, and prompt text redacted.",
            ],
        },
    }
    return {"manifest": manifest, "files": [json_support_bundle_file("manifest.json", manifest)] + files}


async def write_diagnostic_support_export(options: dict[str, Any] | None = None) -> dict[str, Any]:
    opts = options or {}
    env = opts.get("env") or dict(os.environ)
    state_dir = opts.get("stateDir") or _resolve_state_dir(env)
    now = opts.get("now") or datetime.now(timezone.utc)
    output_path = _resolve_output_path({
        "outputPath": opts.get("outputPath"),
        "cwd": opts.get("cwd") or os.getcwd(),
        "env": env,
        "stateDir": state_dir,
        "now": now,
    })
    artifact = await build_diagnostic_support_export({**opts, "env": env, "stateDir": state_dir, "now": now})
    bytes_written = write_support_bundle_zip({"outputPath": output_path, "files": artifact["files"], "compressionLevel": 6})
    return {"path": output_path, "bytes": bytes_written, "manifest": artifact["manifest"]}


__all__ = [
    "DIAGNOSTIC_SUPPORT_EXPORT_VERSION",
    "build_diagnostic_support_export",
    "write_diagnostic_support_export",
]
