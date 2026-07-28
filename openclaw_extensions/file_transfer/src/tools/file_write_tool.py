from __future__ import annotations

import base64
import hashlib
from typing import Any

from openclaw_extensions.file_transfer.shared.audit import append_file_transfer_audit
from openclaw_extensions.file_transfer.shared.params import human_size, read_boolean
from openclaw_extensions.file_transfer.src.tools.descriptors import (
    FILE_TRANSFER_SUBDIR,
    FILE_WRITE_HARD_MAX_BYTES,
    FILE_WRITE_TOOL_DESCRIPTOR,
)
from openclaw_extensions.file_transfer.src.tools.node_tool_invoke import (
    invoke_node_tool_payload,
    read_required_node_path,
)


def _normalize_base64_for_compare(value: str) -> str:
    return value.rstrip("=").replace("-", "+").replace("_", "/")


def _decode_strict_base64(value: str) -> bytes:
    buffer = base64.b64decode(value)
    re_encoded = base64.b64encode(buffer).decode("ascii")
    if _normalize_base64_for_compare(re_encoded) != _normalize_base64_for_compare(value):
        raise ValueError("contentBase64 is not valid base64")
    return buffer


async def _read_source_bytes(
    content_base64: str | None = None,
    source_media_id: str | None = None,
) -> tuple[bytes, str, str]:
    source_media_id = source_media_id.strip() if source_media_id else None
    if source_media_id:
        from openclaw.plugin_sdk.media_store import read_media_buffer
        result = await read_media_buffer(
            source_media_id,
            FILE_TRANSFER_SUBDIR,
            FILE_WRITE_HARD_MAX_BYTES,
        )
        buffer = result.get("buffer", b"")
        return buffer, base64.b64encode(buffer).decode("ascii"), "media"

    if content_base64 is None:
        raise ValueError("contentBase64 or sourceMediaId required")

    buffer = _decode_strict_base64(content_base64)
    return buffer, content_base64, "inline"


async def create_file_write_tool() -> dict:
    descriptor = dict(FILE_WRITE_TOOL_DESCRIPTOR)

    async def _execute(tool_call_id: str, params: dict) -> dict:
        node, file_path = read_required_node_path(params)
        content_base64 = params.get("contentBase64") if isinstance(params.get("contentBase64"), str) else None
        source_media_id = params.get("sourceMediaId") if isinstance(params.get("sourceMediaId"), str) else None
        overwrite = read_boolean(params, "overwrite", False)
        create_parents = read_boolean(params, "createParents", False)

        source_bytes, content_b64, source = await _read_source_bytes(
            content_base64=content_base64,
            source_media_id=source_media_id,
        )
        buffer = source_bytes
        expected_sha256 = hashlib.sha256(buffer).hexdigest()

        node_id, node_display_name, payload, started_at = await invoke_node_tool_payload(
            node=node,
            params=params,
            command="file.write",
            command_params={
                "path": file_path,
                "contentBase64": content_b64,
                "overwrite": overwrite,
                "createParents": create_parents,
                "expectedSha256": expected_sha256,
            },
            invalid_payload_message="unexpected response from node",
            invalid_payload_error="unexpected file.write response from node",
            error_audit_extra={"sizeBytes": len(buffer)},
            require_ok=True,
            requested_path=file_path,
        )

        typed = payload

        import time
        await append_file_transfer_audit(
            {
                "op": "file.write",
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": file_path,
                "canonicalPath": typed.get("path", ""),
                "decision": "allowed",
                "sizeBytes": typed.get("size", 0),
                "sha256": typed.get("sha256", ""),
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )

        overwrite_note = " (overwrote existing file)" if typed.get("overwritten") else ""
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Wrote {typed.get('path', '')} "
                        f"({human_size(typed.get('size', 0))}, "
                        f"sha256:{typed.get('sha256', '')[:12]})"
                        f"{overwrite_note}"
                    ),
                },
            ],
            "details": {**typed, "source": source},
        }

    descriptor["execute"] = _execute
    return descriptor