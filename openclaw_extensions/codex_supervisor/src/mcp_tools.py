"""MCP tool registration plus redaction helpers for Codex Supervisor sessions."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any, TypedDict
from urllib.parse import urlparse, urlunparse

from openclaw_extensions.codex_supervisor.src.supervisor import CodexSupervisor
from openclaw_extensions.codex_supervisor.src.types import (
    CodexSupervisorEndpoint,
    CodexSupervisorSession,
    CodexSupervisorSessionListResult,
)

RAW_TRANSCRIPTS_ENV = "OPENCLAW_CODEX_SUPERVISOR_ALLOW_RAW_TRANSCRIPTS"
WRITE_CONTROLS_ENV = "OPENCLAW_CODEX_SUPERVISOR_ALLOW_WRITE_CONTROLS"

_SECRET_PATTERN = re.compile(
    r"\b(?:sk|glpat|xox[baprs])-[-_a-zA-Z0-9]{12,}\b|\b(?:ghp|gho|ghu|ghs)_[-_a-zA-Z0-9]{12,}\b|\bBearer\s+[-._~+/a-zA-Z0-9]+=*"
)


def redact_string(value: str) -> str:
    return _SECRET_PATTERN.sub("[redacted]", value)


def redact_codex_supervisor_value(value: Any, key: str = "") -> Any:
    if isinstance(value, str):
        if re.search(r"authorization|password|secret|token|api[-_]?key", key, re.IGNORECASE):
            return "[redacted]"
        return redact_string(value)
    if isinstance(value, list):
        return [redact_codex_supervisor_value(entry) for entry in value]
    if not isinstance(value, dict):
        return value
    return {
        entry_key: redact_codex_supervisor_value(entry_value, entry_key)
        for entry_key, entry_value in value.items()
    }


def redact_endpoint_url(value: str) -> str:
    if value.startswith("unix://"):
        return "unix://"
    try:
        parsed = urlparse(value)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc.split("@")[-1],
                parsed.path,
                parsed.params,
                "?[redacted]" if parsed.query else "",
                parsed.fragment,
            )
        )
    except Exception:  # noqa: BLE001
        return "[redacted]"


def redact_codex_supervisor_endpoint(endpoint: CodexSupervisorEndpoint) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": endpoint["id"],
        "transport": endpoint["transport"],
    }
    label = endpoint.get("label")
    if label:
        result["label"] = label
    if endpoint.get("transport") == "websocket" and isinstance(endpoint.get("url"), str):
        result["url"] = redact_endpoint_url(endpoint["url"])
    return result


def raw_transcript_reads_allowed() -> bool:
    return os.environ.get(RAW_TRANSCRIPTS_ENV) == "1"


def write_controls_allowed() -> bool:
    return os.environ.get(WRITE_CONTROLS_ENV) == "1"


def sanitize_session_for_mcp(
    session: CodexSupervisorSession,
    include_transcript_derived_fields: bool,
) -> dict[str, Any]:
    sanitized = redact_codex_supervisor_value(dict(session))
    if not include_transcript_derived_fields:
        sanitized.pop("preview", None)
        sanitized.pop("name", None)
    return sanitized


def sanitize_codex_supervisor_session_list_result(
    result: CodexSupervisorSessionListResult,
    include_transcript_derived_fields: bool | None = None,
) -> dict[str, Any]:
    include_fields = (
        raw_transcript_reads_allowed()
        if include_transcript_derived_fields is None
        else include_transcript_derived_fields
    )
    return {
        "sessions": [
            sanitize_session_for_mcp(session, include_fields) for session in result["sessions"]
        ],
        "errors": (
            redact_codex_supervisor_value(result["errors"])
            if include_fields
            else [{"endpointId": entry["endpointId"], "ok": entry["ok"]} for entry in result["errors"]]
        ),
    }


class CodexSupervisorMcpToolOptions(TypedDict, total=False):
    rawTranscriptReadsAllowed: Callable[[], bool]
    writeControlsAllowed: Callable[[], bool]


def _text_result(text: str, structured_content: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if structured_content is not None:
        result["structuredContent"] = structured_content
    return result


def _error_result(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _raw_transcript_reads_allowed_for(opts: CodexSupervisorMcpToolOptions | None = None) -> bool:
    if opts and opts.get("rawTranscriptReadsAllowed"):
        return opts["rawTranscriptReadsAllowed"]()
    return raw_transcript_reads_allowed()


def _write_controls_allowed_for(opts: CodexSupervisorMcpToolOptions | None = None) -> bool:
    if opts and opts.get("writeControlsAllowed"):
        return opts["writeControlsAllowed"]()
    return write_controls_allowed()


def register_codex_supervisor_mcp_tools(
    server: Any,
    supervisor: CodexSupervisor,
    opts: CodexSupervisorMcpToolOptions | None = None,
) -> None:
    server.tool(
        "codex_endpoint_probe",
        "Check configured Codex app-server endpoints.",
        {},
        lambda: _probe_endpoints(supervisor),
    )

    server.tool(
        "codex_sessions_list",
        "List Codex sessions visible to the OpenClaw supervisor.",
        {
            "include_stored": {"type": "boolean"},
            "max_stored_sessions": {"type": "integer", "minimum": 1, "maximum": 1000},
        },
        lambda include_stored=False, max_stored_sessions=None: _list_sessions(
            supervisor, opts, include_stored, max_stored_sessions
        ),
    )

    server.tool(
        "codex_session_read",
        "Read one Codex session transcript from app-server.",
        {
            "endpoint_id": {"type": "string"},
            "thread_id": {"type": "string", "minLength": 1},
            "include_turns": {"type": "boolean"},
        },
        lambda endpoint_id=None, thread_id="", include_turns=False: _read_session(
            supervisor, opts, endpoint_id, thread_id, include_turns
        ),
    )

    server.tool(
        "codex_session_send",
        "Send text to a Codex session. Idle sessions start a turn; active sessions are steered.",
        {
            "endpoint_id": {"type": "string"},
            "thread_id": {"type": "string", "minLength": 1},
            "text": {"type": "string", "minLength": 1},
            "mode": {"type": "string", "enum": ["auto", "start", "steer"]},
        },
        lambda endpoint_id=None, thread_id="", text="", mode=None: _send_session(
            supervisor, opts, endpoint_id, thread_id, text, mode
        ),
    )

    server.tool(
        "codex_session_interrupt",
        "Interrupt an active Codex turn.",
        {
            "endpoint_id": {"type": "string"},
            "thread_id": {"type": "string", "minLength": 1},
            "turn_id": {"type": "string"},
        },
        lambda endpoint_id=None, thread_id="", turn_id=None: _interrupt_session(
            supervisor, opts, endpoint_id, thread_id, turn_id
        ),
    )


def _probe_endpoints(supervisor: CodexSupervisor) -> dict[str, Any]:
    endpoints = [redact_codex_supervisor_endpoint(endpoint) for endpoint in supervisor.list_endpoints()]
    import asyncio
    health = asyncio.get_event_loop().run_until_complete(supervisor.probe_endpoints())
    health_entries = [
        {"endpointId": entry["endpointId"], "ok": entry["ok"]} for entry in health
    ]
    ok_count = sum(1 for entry in health_entries if entry["ok"])
    return _text_result(
        f"codex endpoints: {ok_count}/{len(health_entries)} ok",
        {"endpoints": endpoints, "health": health_entries},
    )


def _list_sessions(
    supervisor: CodexSupervisor,
    opts: CodexSupervisorMcpToolOptions | None,
    include_stored: bool,
    max_stored_sessions: int | None,
) -> dict[str, Any]:
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        supervisor.list_session_snapshot(
            {"includeStored": include_stored, "maxStoredSessions": max_stored_sessions}
        )
    )
    return _text_result(
        f"codex sessions: {len(result['sessions'])}",
        sanitize_codex_supervisor_session_list_result(
            result, _raw_transcript_reads_allowed_for(opts)
        ),
    )


def _read_session(
    supervisor: CodexSupervisor,
    opts: CodexSupervisorMcpToolOptions | None,
    endpoint_id: str | None,
    thread_id: str,
    include_turns: bool,
) -> dict[str, Any]:
    if not _raw_transcript_reads_allowed_for(opts):
        return _error_result(
            f"Codex session reads are disabled; set {RAW_TRANSCRIPTS_ENV}=1 for a trusted supervisor-only MCP"
        )
    import asyncio
    try:
        response = asyncio.get_event_loop().run_until_complete(
            supervisor.read_session(
                {
                    "endpointId": endpoint_id,
                    "threadId": thread_id,
                    "includeTurns": include_turns,
                }
            )
        )
        return _text_result(
            f"codex session: {thread_id}",
            {"response": redact_codex_supervisor_value(response)},
        )
    except Exception as e:
        return _error_result(str(e))


def _send_session(
    supervisor: CodexSupervisor,
    opts: CodexSupervisorMcpToolOptions | None,
    endpoint_id: str | None,
    thread_id: str,
    text: str,
    mode: str | None,
) -> dict[str, Any]:
    if not _write_controls_allowed_for(opts):
        return _error_result(
            f"Codex write controls are disabled; set {WRITE_CONTROLS_ENV}=1 for a trusted supervisor-only MCP"
        )
    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            supervisor.send_to_session(
                {
                    "endpointId": endpoint_id,
                    "threadId": thread_id,
                    "text": text,
                    "mode": mode,
                }
            )
        )
        return _text_result(
            f"codex {result['mode']}: {result.get('turnId', thread_id)}",
            {"result": result},
        )
    except Exception as e:
        return _error_result(str(e))


def _interrupt_session(
    supervisor: CodexSupervisor,
    opts: CodexSupervisorMcpToolOptions | None,
    endpoint_id: str | None,
    thread_id: str,
    turn_id: str | None,
) -> dict[str, Any]:
    if not _write_controls_allowed_for(opts):
        return _error_result(
            f"Codex write controls are disabled; set {WRITE_CONTROLS_ENV}=1 for a trusted supervisor-only MCP"
        )
    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            supervisor.interrupt_session(
                {
                    "endpointId": endpoint_id,
                    "threadId": thread_id,
                    "turnId": turn_id,
                }
            )
        )
        return _text_result(
            f"codex interrupted: {result['turnId']}",
            {"result": result},
        )
    except Exception as e:
        return _error_result(str(e))
