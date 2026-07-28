from __future__ import annotations

import base64
import hashlib
from openclaw_extensions.file_transfer.shared.audit import append_file_transfer_audit
from openclaw_extensions.file_transfer.shared.mime import (
    IMAGE_MIME_INLINE_SET,
    TEXT_INLINE_MAX_BYTES,
    TEXT_INLINE_MIME_SET,
)
from openclaw_extensions.file_transfer.shared.params import human_size, read_positive_integer_param
from openclaw_extensions.file_transfer.src.tools.descriptors import (
    FILE_FETCH_DEFAULT_MAX_BYTES,
    FILE_FETCH_HARD_MAX_BYTES,
    FILE_FETCH_TOOL_DESCRIPTOR,
    FILE_TRANSFER_SUBDIR,
)
from openclaw_extensions.file_transfer.src.tools.node_tool_invoke import (
    invoke_node_tool_payload,
    read_required_node_path,
)


async def create_file_fetch_tool() -> dict:
    descriptor = dict(FILE_FETCH_TOOL_DESCRIPTOR)

    async def _execute(tool_call_id: str, args: dict) -> dict:
        node, file_path = read_required_node_path(args)
        requested_max = read_positive_integer_param(args, "maxBytes") or FILE_FETCH_DEFAULT_MAX_BYTES
        max_bytes = max(1, min(requested_max, FILE_FETCH_HARD_MAX_BYTES))

        node_id, node_display_name, payload, started_at = await invoke_node_tool_payload(
            node=node,
            params=args,
            command="file.fetch",
            command_params={
                "path": file_path,
                "maxBytes": max_bytes,
            },
            requested_path=file_path,
        )

        canonical_path = payload.get("path", "")
        size = payload.get("size", -1)
        mime_type = payload.get("mimeType", "")
        has_base64 = isinstance(payload.get("base64"), str)
        base64_str = payload.get("base64", "") if has_base64 else ""
        sha256 = payload.get("sha256", "")

        if not canonical_path or size < 0 or not mime_type or not has_base64 or not sha256:
            raise ValueError("invalid file.fetch payload (missing fields)")

        if isinstance(base64_str, str):
            buffer = base64.b64decode(base64_str)
        else:
            buffer = b""

        if len(buffer) != size:
            raise ValueError(
                f"file.fetch size mismatch: payload says {size} bytes, decoded {len(buffer)}"
            )

        local_sha256 = hashlib.sha256(buffer).hexdigest()
        if local_sha256 != sha256:
            raise ValueError("file.fetch sha256 mismatch (integrity failure)")

        from openclaw.plugin_sdk.media_store import save_media_buffer
        saved = await save_media_buffer(
            buffer,
            mime_type,
            FILE_TRANSFER_SUBDIR,
            FILE_FETCH_HARD_MAX_BYTES,
        )
        local_path = saved.get("path", "")
        short_hash = sha256[:12]

        is_inline_image = mime_type in IMAGE_MIME_INLINE_SET
        is_inline_text = mime_type in TEXT_INLINE_MIME_SET and size <= TEXT_INLINE_MAX_BYTES

        content: list[dict] = []
        if is_inline_image:
            content.append({"type": "image", "data": base64_str, "mimeType": mime_type})
        elif is_inline_text:
            text = buffer.decode("utf-8", errors="replace")
            from openclaw.plugin_sdk.security_runtime import wrap_external_content
            wrapped_text = wrap_external_content(
                f"Fetched {canonical_path} ({human_size(size)}, {mime_type}, sha256:{short_hash}) saved at {local_path}\n\n--- contents ---\n{text}",
                source="unknown",
            )
            content.append({"type": "text", "text": wrapped_text})
        else:
            from openclaw.plugin_sdk.security_runtime import wrap_external_content
            wrapped_text = wrap_external_content(
                f"Fetched {canonical_path} ({human_size(size)}, {mime_type}, sha256:{short_hash}) saved at {local_path}",
                source="unknown",
            )
            content.append({"type": "text", "text": wrapped_text})

        import time
        await append_file_transfer_audit(
            {
                "op": "file.fetch",
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": file_path,
                "canonicalPath": canonical_path,
                "decision": "allowed",
                "sizeBytes": size,
                "sha256": sha256,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )

        return {
            "content": content,
            "details": {
                "path": canonical_path,
                "size": size,
                "mimeType": mime_type,
                "sha256": sha256,
                "localPath": local_path,
                "mediaId": saved.get("id"),
                "media": {"mediaUrls": [local_path]},
            },
        }

    descriptor["execute"] = _execute
    return descriptor