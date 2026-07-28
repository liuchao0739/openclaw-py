from __future__ import annotations

import time

from openclaw_extensions.file_transfer.shared.audit import append_file_transfer_audit
from openclaw_extensions.file_transfer.shared.params import read_boolean, read_clamped_int
from openclaw_extensions.file_transfer.src.tools.descriptors import (
    DIR_LIST_DEFAULT_MAX_ENTRIES,
    DIR_LIST_HARD_MAX_ENTRIES,
    DIR_LIST_TOOL_DESCRIPTOR,
)
from openclaw_extensions.file_transfer.src.tools.node_tool_invoke import (
    invoke_node_tool_payload,
    read_required_node_path,
)


async def create_dir_list_tool() -> dict:
    descriptor = dict(DIR_LIST_TOOL_DESCRIPTOR)

    async def _execute(tool_call_id: str, args: dict) -> dict:
        node, dir_path = read_required_node_path(args)

        max_entries = read_clamped_int(
            input_dict=args,
            key="maxEntries",
            default_value=DIR_LIST_DEFAULT_MAX_ENTRIES,
            hard_min=1,
            hard_max=DIR_LIST_HARD_MAX_ENTRIES,
        )

        page_token = args.get("pageToken")
        if isinstance(page_token, str) and page_token.strip():
            page_token = page_token.strip()
        else:
            page_token = None

        node_id, node_display_name, payload, started_at = await invoke_node_tool_payload(
            node=node,
            params=args,
            command="dir.list",
            command_params={
                "path": dir_path,
                "pageToken": page_token,
                "maxEntries": max_entries,
            },
            requested_path=dir_path,
        )

        canonical_path = payload.get("path", dir_path)

        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            entries = []
        truncated = payload.get("truncated", False) is True
        next_page_token = payload.get("nextPageToken")
        if not isinstance(next_page_token, str):
            next_page_token = None

        file_count = sum(1 for e in entries if not e.get("isDir", False))
        dir_count = sum(1 for e in entries if e.get("isDir", False))
        truncated_note = " (more entries available — pass nextPageToken)" if truncated else ""
        files_word = "file" if file_count != 1 else "files"
        dirs_word = "subdirectory" if dir_count != 1 else "subdirectories"
        summary = f"Listed {canonical_path}: {file_count} {files_word}, {dir_count} {dirs_word}{truncated_note}"

        await append_file_transfer_audit(
            {
                "op": "dir.list",
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": dir_path,
                "canonicalPath": canonical_path,
                "decision": "allowed",
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )

        details: dict = {
            "path": canonical_path,
            "entries": entries,
            "truncated": truncated,
        }
        if next_page_token is not None:
            details["nextPageToken"] = next_page_token

        return {
            "content": [{"type": "text", "text": summary}],
            "details": details,
        }

    descriptor["execute"] = _execute
    return descriptor