from __future__ import annotations

from typing import Any, Literal, TypedDict


FileTransferErrCode = Literal[
    "INVALID_PATH",
    "INVALID_BASE64",
    "INVALID_PARAMS",
    "NOT_FOUND",
    "PERMISSION_DENIED",
    "IS_DIRECTORY",
    "IS_FILE",
    "PARENT_NOT_FOUND",
    "EXISTS_NO_OVERWRITE",
    "READ_ERROR",
    "WRITE_ERROR",
    "FILE_TOO_LARGE",
    "TREE_TOO_LARGE",
    "PATH_TRAVERSAL",
    "SYMLINK_TARGET_DENIED",
    "INTEGRITY_FAILURE",
    "POLICY_DENIED",
    "NO_POLICY",
]


class FileTransferErr(TypedDict, total=False):
    ok: Literal[False]
    code: FileTransferErrCode
    message: str
    canonicalPath: str


def err(code: FileTransferErrCode, message: str, canonical_path: str | None = None) -> FileTransferErr:
    result: FileTransferErr = {
        "ok": False,
        "code": code,
        "message": message,
    }
    if canonical_path is not None:
        result["canonicalPath"] = canonical_path
    return result


def throw_from_node_payload(operation: str, payload: dict[str, Any]) -> None:
    code = payload.get("code", "ERROR")
    if not isinstance(code, str):
        code = "ERROR"
    message = payload.get("message", f"{operation} failed")
    if not isinstance(message, str):
        message = f"{operation} failed"
    canonical = payload.get("canonicalPath")
    canonical_str = f" (canonical={canonical})" if isinstance(canonical, str) else ""
    raise RuntimeError(f"{operation} {code}: {message}{canonical_str}")