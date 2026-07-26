"""MCP tool registration plus redaction helpers for Codex Supervisor sessions."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse, urlunparse

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


CodexSupervisorMcpToolOptions = dict[str, Callable[[], bool] | None]
