from __future__ import annotations

import os
from typing import Any, Literal, TypedDict


class InvalidPathResult(TypedDict):
    ok: Literal[False]
    code: Literal["INVALID_PATH"]
    message: str


SYMLINK_REJECTED_MESSAGE = (
    "path traverses a symlink; refusing because followSymlinks=false "
    "(set plugins.entries.file-transfer.config.nodes.<node>.followSymlinks=true to allow, "
    "or update allowReadPaths to the canonical path)"
)

FsSafeReadErrorCode = Literal["INVALID_PATH", "NOT_FOUND", "SYMLINK_REDIRECT"]


def classify_fs_safe_read_error(err: Any) -> FsSafeReadErrorCode | None:
    if not isinstance(err, Exception):
        return None
    code = getattr(err, "code", None)
    if code == "not-found":
        return "NOT_FOUND"
    if code == "symlink":
        return "SYMLINK_REDIRECT"
    if code == "invalid-path":
        return "INVALID_PATH"
    return None


def read_absolute_path(input_val: Any) -> str | InvalidPathResult:
    if not isinstance(input_val, str) or len(input_val) == 0:
        return {"ok": False, "code": "INVALID_PATH", "message": "path required"}
    if "\0" in input_val:
        return {"ok": False, "code": "INVALID_PATH", "message": "path contains NUL byte"}
    if not os.path.isabs(input_val):
        return {"ok": False, "code": "INVALID_PATH", "message": "path must be absolute"}
    return input_val


def canonical_path_from_fs_safe_error(err: Any) -> str | None:
    if not isinstance(err, Exception):
        return None
    cause = getattr(err, "cause", None)
    if cause and isinstance(cause, dict) and "canonicalPath" in cause:
        cp = cause["canonicalPath"]
        if isinstance(cp, str):
            return cp
    return None


async def resolve_canonical_read_path(
    requested_path: str,
    follow_symlinks: bool,
    classify_error: Any,
    not_found_message: str,
) -> str | dict[str, Any]:
    from openclaw.plugin_sdk.security_runtime import resolve_absolute_path_for_read

    try:
        result = await resolve_absolute_path_for_read(
            requested_path,
            symlinks="follow" if follow_symlinks else "reject",
        )
        return result["canonicalPath"]
    except Exception as err:
        code = classify_error(err)
        canonical_path = canonical_path_from_fs_safe_error(err)
        if code == "NOT_FOUND":
            message = not_found_message
        elif code == "SYMLINK_REDIRECT":
            message = SYMLINK_REJECTED_MESSAGE
        elif code:
            message = f"realpath failed: {err}"
        else:
            message = f"realpath failed: {err}"
        result: dict[str, Any] = {
            "ok": False,
            "code": code or "READ_ERROR",
            "message": message,
        }
        if canonical_path:
            result["canonicalPath"] = canonical_path
        return result


async def stat_required_directory(
    canonical_path: str,
    classify_error: Any,
) -> dict[str, Any]:
    import aiofiles
    import aiofiles.os

    try:
        stats = await aiofiles.os.stat(canonical_path)
    except Exception as err:
        code = classify_error(err)
        return {
            "ok": False,
            "code": code or "READ_ERROR",
            "message": f"stat failed: {err}",
            "canonicalPath": canonical_path,
        }

    import stat as stat_module
    if not stat_module.S_ISDIR(stats.st_mode):
        return {
            "ok": False,
            "code": "IS_FILE",
            "message": "path is not a directory",
            "canonicalPath": canonical_path,
        }
    return {"ok": True}