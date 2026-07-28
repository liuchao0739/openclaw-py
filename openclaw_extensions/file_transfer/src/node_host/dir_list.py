from __future__ import annotations

import os
import time
from typing import Any, Literal, TypedDict

from openclaw_extensions.file_transfer.src.node_host.path_errors import (
    classify_fs_safe_read_error,
    read_absolute_path,
    resolve_canonical_read_path,
    stat_required_directory,
)
from openclaw_extensions.file_transfer.src.shared.mime import mime_from_extension

DIR_LIST_DEFAULT_MAX_ENTRIES = 200
DIR_LIST_HARD_MAX_ENTRIES = 5000


class DirListParams(TypedDict, total=False):
    path: Any
    pageToken: Any
    maxEntries: Any
    followSymlinks: Any


class DirListEntry(TypedDict):
    name: str
    path: str
    size: int
    mimeType: str
    isDir: bool
    mtime: int


class DirListOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    entries: list[DirListEntry]
    nextPageToken: str
    truncated: bool


DirListErrCode = Literal[
    "INVALID_PATH",
    "NOT_FOUND",
    "PERMISSION_DENIED",
    "IS_FILE",
    "SYMLINK_REDIRECT",
    "READ_ERROR",
]


class DirListErr(TypedDict, total=False):
    ok: Literal[False]
    code: DirListErrCode
    message: str
    canonicalPath: str


DirListResult = DirListOk | DirListErr


def _clamp_max_entries(value: Any) -> int:
    if not isinstance(value, (int, float)) or value != value or value <= 0:
        return DIR_LIST_DEFAULT_MAX_ENTRIES
    return min(int(value), DIR_LIST_HARD_MAX_ENTRIES)


def _parse_page_offset(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _classify_fs_error(err: Any) -> DirListErrCode:
    safe_code = classify_fs_safe_read_error(err)
    if safe_code:
        return safe_code
    code = getattr(err, "code", None)
    if code == "ENOENT":
        return "NOT_FOUND"
    if code in ("EACCES", "EPERM"):
        return "PERMISSION_DENIED"
    return "READ_ERROR"


async def handle_dir_list(params: DirListParams) -> DirListResult:
    requested_path = read_absolute_path(params.get("path"))
    if not isinstance(requested_path, str):
        return requested_path

    max_entries = _clamp_max_entries(params.get("maxEntries"))
    offset = _parse_page_offset(params.get("pageToken"))
    follow_symlinks = params.get("followSymlinks") is True

    canonical = await resolve_canonical_read_path(
        requested_path,
        follow_symlinks,
        _classify_fs_error,
        "path not found",
    )
    if not isinstance(canonical, str):
        return canonical

    directory = await stat_required_directory(canonical, _classify_fs_error)
    if not directory.get("ok"):
        return directory

    try:
        from openclaw.plugin_sdk.security_runtime import root
        dir_root = await root(canonical)
        listed_entries = await dir_root.list(".", withFileTypes=True)
    except Exception as err:
        code = _classify_fs_error(err)
        return {
            "ok": False,
            "code": code,
            "message": f"list failed: {err}",
            "canonicalPath": canonical,
        }

    if isinstance(listed_entries, list):
        listed_entries.sort(key=lambda e: e.get("name", ""))
    else:
        listed_entries = []

    total = len(listed_entries)
    page = listed_entries[offset : offset + max_entries]
    truncated = offset + max_entries < total
    next_page_token = str(offset + max_entries) if truncated else None

    entries: list[DirListEntry] = []
    for entry in page:
        entry_name = entry.get("name", "")
        entry_path = os.path.join(canonical, entry_name)
        is_dir = entry.get("isDirectory", False)
        size = entry.get("size", 0)
        mtime = entry.get("mtimeMs", int(time.time() * 1000))
        if isinstance(mtime, float):
            mtime = int(mtime)

        entries.append(
            {
                "name": entry_name,
                "path": entry_path,
                "size": 0 if is_dir else size,
                "mimeType": "inode/directory" if is_dir else mime_from_extension(entry_name),
                "isDir": is_dir,
                "mtime": mtime,
            }
        )

    result: DirListOk = {
        "ok": True,
        "path": canonical,
        "entries": entries,
    }
    if next_page_token is not None:
        result["nextPageToken"] = next_page_token
    result["truncated"] = truncated
    return result