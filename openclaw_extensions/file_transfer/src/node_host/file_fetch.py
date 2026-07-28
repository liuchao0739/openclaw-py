from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Literal, TypedDict

from openclaw_extensions.file_transfer.src.node_host.path_errors import (
    classify_fs_safe_read_error,
    read_absolute_path,
    resolve_canonical_read_path,
)

FILE_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
FILE_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024
TEXT_SNIFF_MAX_BYTES = 8192


class FileFetchParams(TypedDict, total=False):
    path: Any
    maxBytes: Any
    followSymlinks: Any
    preflightOnly: Any


class FileFetchOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    size: int
    mimeType: str
    base64: str
    sha256: str
    preflightOnly: bool


FileFetchErrCode = Literal[
    "INVALID_PATH",
    "NOT_FOUND",
    "PERMISSION_DENIED",
    "IS_DIRECTORY",
    "FILE_TOO_LARGE",
    "PATH_TRAVERSAL",
    "SYMLINK_REDIRECT",
    "READ_ERROR",
]


class FileFetchErr(TypedDict, total=False):
    ok: Literal[False]
    code: FileFetchErrCode
    message: str
    canonicalPath: str


FileFetchResult = FileFetchOk | FileFetchErr


def _clamp_max_bytes(value: Any) -> int:
    if not isinstance(value, (int, float)) or value != value or value <= 0:
        return FILE_FETCH_DEFAULT_MAX_BYTES
    return min(int(value), FILE_FETCH_HARD_MAX_BYTES)


def _classify_fs_error(err: Any) -> FileFetchErrCode:
    safe_code = classify_fs_safe_read_error(err)
    if safe_code:
        return safe_code
    code = getattr(err, "code", None)
    if code == "not-file":
        return "IS_DIRECTORY"
    if code == "ENOENT":
        return "NOT_FOUND"
    if code in ("EACCES", "EPERM"):
        return "PERMISSION_DENIED"
    if code == "EISDIR":
        return "IS_DIRECTORY"
    return "READ_ERROR"


def _is_likely_plain_text(data: bytes) -> bool:
    if len(data) == 0:
        return True
    sample = data[:TEXT_SNIFF_MAX_BYTES]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return False
    control_bytes = sum(1 for b in sample if b < 0x20 and b not in (0x09, 0x0A, 0x0D))
    return control_bytes / len(sample) < 0.01


async def _detect_fetched_file_mime(data: bytes, file_path: str) -> str:
    try:
        from openclaw.plugin_sdk.media_mime import detect_mime
        detected = await detect_mime({"buffer": data, "filePath": file_path})
        if detected:
            return detected
    except Exception:
        pass
    return "text/plain" if _is_likely_plain_text(data) else "application/octet-stream"


async def handle_file_fetch(params: FileFetchParams) -> FileFetchResult:
    requested_path = read_absolute_path(params.get("path"))
    if not isinstance(requested_path, str):
        return requested_path

    max_bytes = _clamp_max_bytes(params.get("maxBytes"))
    follow_symlinks = params.get("followSymlinks") is True
    preflight_only = params.get("preflightOnly") is True

    canonical = await resolve_canonical_read_path(
        requested_path,
        follow_symlinks,
        _classify_fs_error,
        "file not found",
    )
    if not isinstance(canonical, str):
        return canonical

    try:
        from openclaw.plugin_sdk.security_runtime import root

        parent_root = await root(os.path.dirname(canonical))
        opened = await parent_root.open(os.path.basename(canonical))
    except Exception as err:
        code = _classify_fs_error(err)
        return {
            "ok": False,
            "code": code,
            "message": "path is a directory" if code == "IS_DIRECTORY" else f"open failed: {err}",
            "canonicalPath": canonical,
        }

    try:
        stats = opened.get("stat", {})
        size = stats.get("size", 0)
        if size > max_bytes:
            return {
                "ok": False,
                "code": "FILE_TOO_LARGE",
                "message": f"file size {size} exceeds limit {max_bytes}",
                "canonicalPath": opened.get("realPath", canonical),
            }

        if preflight_only:
            return {
                "ok": True,
                "path": opened.get("realPath", canonical),
                "size": size,
                "mimeType": "",
                "base64": "",
                "sha256": "",
                "preflightOnly": True,
            }

        handle = opened.get("handle")
        if handle and hasattr(handle, "readFile"):
            buffer = await handle.readFile()
        elif handle and hasattr(handle, "read"):
            buffer = await handle.read()
        else:
            with open(canonical, "rb") as f:
                buffer = f.read()

        if isinstance(buffer, str):
            buffer = buffer.encode("utf-8")
        if len(buffer) > max_bytes:
            return {
                "ok": False,
                "code": "FILE_TOO_LARGE",
                "message": f"read {len(buffer)} bytes exceeds limit {max_bytes}",
                "canonicalPath": opened.get("realPath", canonical),
            }

        sha256 = hashlib.sha256(buffer).hexdigest()
        base64_str = base64.b64encode(buffer).decode("ascii")
        mimeType = await _detect_fetched_file_mime(buffer, opened.get("realPath", canonical))

        return {
            "ok": True,
            "path": opened.get("realPath", canonical),
            "size": len(buffer),
            "mimeType": mimeType,
            "base64": base64_str,
            "sha256": sha256,
        }
    except Exception as err:
        code = _classify_fs_error(err)
        return {
            "ok": False,
            "code": code,
            "message": f"read failed: {err}",
            "canonicalPath": opened.get("realPath", canonical),
        }
    finally:
        handle = opened.get("handle")
        if handle and hasattr(handle, "close"):
            try:
                await handle.close()
            except Exception:
                pass