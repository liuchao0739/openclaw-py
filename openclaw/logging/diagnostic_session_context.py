"""Diagnostic session context helpers for support bundles.

Mirrors src/logging/diagnostic-session-context.ts.
"""

from __future__ import annotations

import json
import os
from typing import Any

SESSION_TAIL_BYTES = 64 * 1024
MAX_QUOTED_FIELD_CHARS = 140


def _quote_log_field(value: str) -> str:
    one_line = " ".join(value.split())
    one_line = one_line.strip()
    if len(one_line) > MAX_QUOTED_FIELD_CHARS:
        one_line = one_line[: max(0, MAX_QUOTED_FIELD_CHARS - 3)] + "..."
    escaped = one_line.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_cron_run_session_key(session_key: str | None) -> dict[str, Any]:
    parts = (session_key or "").strip().split(":") if session_key else []
    if not parts or parts[0] != "agent":
        return {}
    cron_index = -1
    try:
        cron_index = parts.index("cron")
    except ValueError:
        pass
    if cron_index < 2:
        return {}
    run_index = -1
    try:
        run_index = parts.index("run", cron_index + 2)
    except ValueError:
        pass
    result: dict[str, Any] = {"agentId": parts[1], "cronJobId": parts[cron_index + 1]}
    if run_index >= 0:
        result["cronRunId"] = parts[run_index + 1]
    return result


def _resolve_state_dir() -> str:
    try:
        from openclaw.config.paths import resolve_state_dir
        return resolve_state_dir()
    except Exception:
        return os.environ.get("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))


def _resolve_session_file(params: dict[str, Any]) -> str | None:
    agent_id = (params.get("agentId") or "").strip() if params.get("agentId") else ""
    run_id = ""
    if params.get("activeSessionId"):
        run_id = params["activeSessionId"].strip()
    elif params.get("cronRunId"):
        run_id = params["cronRunId"].strip()
    if not agent_id or not run_id:
        return None
    return os.path.join(_resolve_state_dir(), "agents", agent_id, "sessions", f"{run_id}.jsonl")


def _read_tail_text(file_path: str) -> dict[str, Any] | None:
    try:
        stat = os.stat(file_path)
        if stat.st_size <= 0:
            return None
        length = min(stat.st_size, SESSION_TAIL_BYTES)
        start = max(0, stat.st_size - length)
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(length)
        return {"text": data.decode("utf-8", errors="replace"), "truncated": start > 0}
    except OSError:
        return None


def _text_from_content(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    texts = []
    for part in content:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return " ".join(texts) if texts else None


def read_last_assistant_from_session_file(file_path: str | None) -> str | None:
    if not file_path:
        return None
    tail = _read_tail_text(file_path)
    if not tail or not tail.get("text"):
        return None
    lines = [line for line in tail["text"].splitlines() if line]
    if tail.get("truncated") and lines:
        lines.pop(0)
    for index in range(len(lines) - 1, -1, -1):
        try:
            parsed = json.loads(lines[index])
            message = parsed.get("message") or {}
            if message.get("role") != "assistant":
                continue
            text = _text_from_content(message.get("content"))
            if text and text.strip():
                return text.strip()
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _read_cron_job_name(cron_job_id: str | None) -> str | None:
    if not cron_job_id:
        return None
    try:
        from openclaw.cron.store import load_cron_jobs_store_sync, resolve_cron_jobs_store_path
        store = load_cron_jobs_store_sync(resolve_cron_jobs_store_path())
        for entry in store.get("jobs", []):
            if entry.get("id") == cron_job_id:
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return None
    except Exception:
        return None


def resolve_cron_session_diagnostic_context(params: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_cron_run_session_key(params.get("sessionKey"))
    if not parsed.get("cronJobId") and not parsed.get("cronRunId"):
        return {}
    context: dict[str, Any] = dict(parsed)
    context["cronJobName"] = _read_cron_job_name(parsed.get("cronJobId"))
    context["lastAssistant"] = read_last_assistant_from_session_file(
        _resolve_session_file({**parsed, "activeSessionId": params.get("activeSessionId")})
    )
    return context


def format_cron_session_diagnostic_fields(context: dict[str, Any]) -> str:
    fields: list[str] = []
    if context.get("cronJobId"):
        fields.append(f"cronJobId={context['cronJobId']}")
    if context.get("cronRunId"):
        fields.append(f"cronRunId={context['cronRunId']}")
    if context.get("cronJobName"):
        fields.append(f"cronJob={_quote_log_field(context['cronJobName'])}")
    if context.get("lastAssistant"):
        fields.append(f"lastAssistant={_quote_log_field(context['lastAssistant'])}")
    return " ".join(fields)


def format_stopped_cron_session_diagnostic_fields(context: dict[str, Any]) -> str:
    fields: list[str] = []
    if context.get("cronJobName"):
        fields.append(f"stopped={_quote_log_field(context['cronJobName'])}")
    rest = format_cron_session_diagnostic_fields({
        "cronJobId": context.get("cronJobId"),
        "cronRunId": context.get("cronRunId"),
        "lastAssistant": context.get("lastAssistant"),
    })
    if rest:
        fields.append(rest)
    return " ".join(fields)


__all__ = [
    "parse_cron_run_session_key",
    "read_last_assistant_from_session_file",
    "resolve_cron_session_diagnostic_context",
    "format_cron_session_diagnostic_fields",
    "format_stopped_cron_session_diagnostic_fields",
]
