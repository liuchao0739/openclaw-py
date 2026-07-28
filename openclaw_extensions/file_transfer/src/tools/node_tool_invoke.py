from __future__ import annotations

import base64
import hashlib
import time
import uuid
from typing import Any

from openclaw_extensions.file_transfer.shared.audit import (
    FileTransferAuditOp,
    append_file_transfer_audit,
)
from openclaw_extensions.file_transfer.shared.errors import throw_from_node_payload
from openclaw_extensions.file_transfer.shared.params import (
    read_gateway_call_options,
    read_trimmed_string,
)


def read_required_node_path(params: dict[str, Any]) -> tuple[str, str]:
    node = read_trimmed_string(params, "node")
    requested_path = read_trimmed_string(params, "path")
    if not node:
        raise ValueError("node required")
    if not requested_path:
        raise ValueError("path required")
    return node, requested_path


async def invoke_node_tool_payload(
    node: str,
    params: dict[str, Any],
    command: FileTransferAuditOp,
    command_params: dict[str, Any],
    requested_path: str,
    error_audit_extra: dict[str, Any] | None = None,
    invalid_payload_error: str | None = None,
    invalid_payload_message: str | None = None,
    require_ok: bool = False,
) -> tuple[str, str, dict[str, Any], float]:
    from openclaw.plugin_sdk.agent_harness_runtime import call_gateway_tool, list_nodes, resolve_node_id_from_list

    gateway_opts = read_gateway_call_options(params)
    nodes = await list_nodes(gateway_opts)
    if not nodes:
        raise ValueError(
            "no paired nodes available; file-transfer tools require a paired node from nodes status. "
            "Use local file/exec tools for local workspace paths."
        )
    node_id = resolve_node_id_from_list(nodes, node, False)
    node_meta = next((n for n in nodes if n.get("nodeId") == node_id), None)
    node_display_name = node_meta.get("displayName", node) if node_meta else node
    started_at = time.time()

    raw = await call_gateway_tool(
        "node.invoke",
        gateway_opts,
        {
            "nodeId": node_id,
            "command": command,
            "params": command_params,
            "idempotencyKey": str(uuid.uuid4()),
        },
    )

    payload = None
    raw_payload = raw.get("payload") if raw else None
    if raw_payload and isinstance(raw_payload, dict):
        payload = raw_payload

    if payload is None:
        extra = error_audit_extra or {}
        await append_file_transfer_audit(
            {
                "op": command,
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": requested_path,
                "decision": "error",
                "errorMessage": invalid_payload_message or "invalid payload",
                "durationMs": int((time.time() - started_at) * 1000),
                **extra,
            }
        )
        raise ValueError(invalid_payload_error or f"invalid {command} payload")

    if payload.get("ok") is False or (require_ok and payload.get("ok") is not True):
        extra = error_audit_extra or {}
        await append_file_transfer_audit(
            {
                "op": command,
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": requested_path,
                "canonicalPath": payload.get("canonicalPath") if isinstance(payload.get("canonicalPath"), str) else None,
                "decision": "error",
                "errorCode": payload.get("code") if isinstance(payload.get("code"), str) else None,
                "errorMessage": payload.get("message") if isinstance(payload.get("message"), str) else None,
                "durationMs": int((time.time() - started_at) * 1000),
                **extra,
            }
        )
        throw_from_node_payload(command, payload)

    return node_id, node_display_name, payload, started_at