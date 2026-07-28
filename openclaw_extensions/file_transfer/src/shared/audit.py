from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict


FileTransferAuditOp = Literal["file.fetch", "dir.list", "dir.fetch", "file.write"]

FileTransferAuditDecision = Literal[
    "allowed",
    "allowed:once",
    "allowed:always",
    "denied:no_policy",
    "denied:policy",
    "denied:approval",
    "denied:command_not_allowed",
    "denied:symlink_escape",
    "error",
]


class FileTransferAuditRecord(TypedDict, total=False):
    timestamp: str
    op: FileTransferAuditOp
    nodeId: str
    nodeDisplayName: str
    requestedPath: str
    canonicalPath: str
    decision: FileTransferAuditDecision
    errorCode: str
    errorMessage: str
    sizeBytes: int
    sha256: str
    durationMs: int
    requesterAgentId: str
    sessionKey: str
    reason: str


_audit_dir: str | None = None
_audit_dir_lock = threading.Lock()


def _ensure_audit_dir() -> str:
    global _audit_dir
    with _audit_dir_lock:
        if _audit_dir is not None:
            return _audit_dir
        audit_dir = os.path.join(os.path.expanduser("~"), ".openclaw", "audit")
        os.makedirs(audit_dir, exist_ok=True, mode=0o700)
        _audit_dir = audit_dir
        return audit_dir


def _audit_file_path(dir_path: str) -> str:
    return os.path.join(dir_path, "file-transfer.jsonl")


async def append_file_transfer_audit(record: FileTransferAuditRecord) -> None:
    try:
        from openclaw.plugin_sdk.security_runtime import append_regular_file

        audit_dir = _ensure_audit_dir()
        record_with_ts: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        line = json.dumps(record_with_ts) + "\n"
        await append_regular_file(
            file_path=_audit_file_path(audit_dir),
            content=line,
            reject_symlink_parents=True,
        )
    except Exception as e:
        import sys
        sys.stderr.write(f"[file-transfer:audit] append failed: {e}\n")