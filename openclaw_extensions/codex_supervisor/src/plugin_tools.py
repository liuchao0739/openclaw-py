"""OpenClaw agent-tool definitions for Codex Supervisor endpoint and session controls."""

from __future__ import annotations

import json
from typing import Any, TypedDict

from openclaw.agents.tools.common import read_string_param
from openclaw_extensions.codex_supervisor.src.mcp_tools import (
    redact_codex_supervisor_endpoint,
    redact_codex_supervisor_value,
    sanitize_codex_supervisor_session_list_result,
)
from openclaw_extensions.codex_supervisor.src.supervisor import CodexSupervisor
from openclaw_extensions.codex_supervisor.src.types import CodexSupervisorTurnMode

_EMPTY_PARAMS_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {}}

_SESSIONS_LIST_PARAMS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "include_stored": {"type": "boolean"},
        "max_stored_sessions": {"type": "integer", "minimum": 1, "maximum": 1000},
    },
}

_SESSION_READ_PARAMS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["thread_id"],
    "properties": {
        "endpoint_id": {"type": "string"},
        "thread_id": {"type": "string"},
        "include_turns": {"type": "boolean"},
    },
}

_SESSION_SEND_PARAMS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["thread_id", "text"],
    "properties": {
        "endpoint_id": {"type": "string"},
        "thread_id": {"type": "string"},
        "text": {"type": "string"},
        "mode": {"type": "string", "enum": ["auto", "start", "steer"]},
    },
}

_SESSION_INTERRUPT_PARAMS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["thread_id"],
    "properties": {
        "endpoint_id": {"type": "string"},
        "thread_id": {"type": "string"},
        "turn_id": {"type": "string"},
    },
}


class CodexSupervisorToolPolicy(TypedDict):
    allowRawTranscripts: bool
    allowWriteControls: bool


class CodexSupervisorToolOptions(TypedDict):
    supervisor: CodexSupervisor
    policy: CodexSupervisorToolPolicy


def as_record(params: Any) -> dict[str, Any]:
    return params if isinstance(params, dict) else {}


def read_boolean_param(params: dict[str, Any], key: str) -> bool:
    return params.get(key) is True


def read_integer_param(params: dict[str, Any], key: str) -> int | None:
    value = params.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    if value < 1 or value > 1000:
        raise ValueError(f"{key} must be between 1 and 1000")
    return value


def read_mode_param(params: dict[str, Any]) -> CodexSupervisorTurnMode | None:
    mode = read_string_param(params, "mode")
    if not mode:
        return None
    if mode in ("auto", "start", "steer"):
        return mode  # type: ignore[return-value]
    raise ValueError("mode must be auto, start, or steer")


def require_raw_transcript_access(policy: CodexSupervisorToolPolicy) -> None:
    if not policy["allowRawTranscripts"]:
        raise RuntimeError("Codex session reads are disabled for this codex-supervisor plugin config.")


def require_write_access(policy: CodexSupervisorToolPolicy) -> None:
    if not policy["allowWriteControls"]:
        raise RuntimeError("Codex write controls are disabled for this codex-supervisor plugin config.")


def json_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "details": payload,
    }


def create_codex_supervisor_tools(options: CodexSupervisorToolOptions) -> list[dict[str, Any]]:
    supervisor = options["supervisor"]
    policy = options["policy"]

    async def probe_execute(_tool_call_id: str | None = None, _raw_params: Any = None) -> dict[str, Any]:
        endpoints = [redact_codex_supervisor_endpoint(endpoint) for endpoint in supervisor.list_endpoints()]
        health = [
            {"endpointId": entry["endpointId"], "ok": entry["ok"]}
            for entry in await supervisor.probe_endpoints()
        ]
        ok_count = sum(1 for entry in health if entry["ok"])
        return json_result(
            {
                "summary": f"codex endpoints: {ok_count}/{len(health)} ok",
                "endpoints": endpoints,
                "health": health,
            }
        )

    async def sessions_list_execute(_tool_call_id: str | None = None, raw_params: Any = None) -> dict[str, Any]:
        params = as_record(raw_params)
        result = await supervisor.list_session_snapshot(
            {
                "includeStored": read_boolean_param(params, "include_stored"),
                "maxStoredSessions": read_integer_param(params, "max_stored_sessions"),
            }
        )
        sanitized = sanitize_codex_supervisor_session_list_result(result, policy["allowRawTranscripts"])
        return json_result(
            {
                "summary": f"codex sessions: {len(result['sessions'])}",
                **sanitized,
            }
        )

    async def session_read_execute(_tool_call_id: str | None = None, raw_params: Any = None) -> dict[str, Any]:
        require_raw_transcript_access(policy)
        params = as_record(raw_params)
        thread_id = read_string_param(params, "thread_id", required=True)
        assert thread_id is not None
        response = await supervisor.read_session(
            {
                "endpointId": read_string_param(params, "endpoint_id"),
                "threadId": thread_id,
                "includeTurns": read_boolean_param(params, "include_turns"),
            }
        )
        return json_result(
            {
                "summary": f"codex session: {thread_id}",
                "response": redact_codex_supervisor_value(response),
            }
        )

    async def session_send_execute(_tool_call_id: str | None = None, raw_params: Any = None) -> dict[str, Any]:
        require_write_access(policy)
        params = as_record(raw_params)
        thread_id = read_string_param(params, "thread_id", required=True)
        text = read_string_param(params, "text", required=True, allow_empty=False)
        assert thread_id is not None
        assert text is not None
        result = await supervisor.send_to_session(
            {
                "endpointId": read_string_param(params, "endpoint_id"),
                "threadId": thread_id,
                "text": text,
                "mode": read_mode_param(params),
            }
        )
        return json_result(
            {
                "summary": f"codex {result['mode']}: {result.get('turnId', thread_id)}",
                "result": result,
            }
        )

    async def session_interrupt_execute(
        _tool_call_id: str | None = None,
        raw_params: Any = None,
    ) -> dict[str, Any]:
        require_write_access(policy)
        params = as_record(raw_params)
        thread_id = read_string_param(params, "thread_id", required=True)
        assert thread_id is not None
        result = await supervisor.interrupt_session(
            {
                "endpointId": read_string_param(params, "endpoint_id"),
                "threadId": thread_id,
                "turnId": read_string_param(params, "turn_id"),
            }
        )
        return json_result(
            {
                "summary": f"codex interrupted: {result['turnId']}",
                "result": result,
            }
        )

    return [
        {
            "name": "codex_endpoint_probe",
            "label": "Codex Endpoint Probe",
            "description": "Check configured Codex app-server endpoints.",
            "parameters": _EMPTY_PARAMS_SCHEMA,
            "execute": probe_execute,
        },
        {
            "name": "codex_sessions_list",
            "label": "Codex Sessions List",
            "description": "List Codex sessions visible to the OpenClaw supervisor.",
            "parameters": _SESSIONS_LIST_PARAMS_SCHEMA,
            "execute": sessions_list_execute,
        },
        {
            "name": "codex_session_read",
            "label": "Codex Session Read",
            "description": "Read one Codex session transcript from app-server.",
            "parameters": _SESSION_READ_PARAMS_SCHEMA,
            "execute": session_read_execute,
        },
        {
            "name": "codex_session_send",
            "label": "Codex Session Send",
            "description": (
                "Send text to a Codex session. Idle sessions start a turn; active sessions are steered."
            ),
            "parameters": _SESSION_SEND_PARAMS_SCHEMA,
            "execute": session_send_execute,
        },
        {
            "name": "codex_session_interrupt",
            "label": "Codex Session Interrupt",
            "description": "Interrupt an active Codex turn.",
            "parameters": _SESSION_INTERRUPT_PARAMS_SCHEMA,
            "execute": session_interrupt_execute,
        },
    ]
