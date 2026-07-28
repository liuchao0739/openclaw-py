from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import platform
import re
import subprocess
from typing import Any, Literal, TypedDict

from openclaw_extensions.file_transfer.src.node_host.path_errors import (
    classify_fs_safe_read_error,
    read_absolute_path,
    resolve_canonical_read_path,
    stat_required_directory,
)

DIR_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
DIR_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024


class DirFetchParams(TypedDict, total=False):
    path: Any
    maxBytes: Any
    includeDotfiles: Any
    followSymlinks: Any
    preflightOnly: Any


class DirFetchOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    tarBase64: str
    tarBytes: int
    sha256: str
    fileCount: int
    entries: list[str]
    preflightOnly: bool


DirFetchErrCode = Literal[
    "INVALID_PATH",
    "NOT_FOUND",
    "IS_FILE",
    "TREE_TOO_LARGE",
    "SYMLINK_REDIRECT",
    "READ_ERROR",
]


class DirFetchErr(TypedDict, total=False):
    ok: Literal[False]
    code: DirFetchErrCode
    message: str
    canonicalPath: str


DirFetchResult = DirFetchOk | DirFetchErr


def _clamp_max_bytes(value: Any) -> int:
    if not isinstance(value, (int, float)) or value != value or value <= 0:
        return DIR_FETCH_DEFAULT_MAX_BYTES
    return min(int(value), DIR_FETCH_HARD_MAX_BYTES)


def _classify_fs_error(err: Any) -> DirFetchErrCode:
    safe_code = classify_fs_safe_read_error(err)
    if safe_code:
        return safe_code
    code = getattr(err, "code", None)
    if code == "ENOENT":
        return "NOT_FOUND"
    return "READ_ERROR"


async def _preflight_du(dir_path: str, max_bytes: int) -> bool:
    heuristic_kb = -(-(max_bytes * 4) // 1024)
    try:
        du_bin = "du"
        proc = await asyncio.create_subprocess_exec(
            du_bin, "-sk", dir_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout_data, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout_data.decode("utf-8", errors="replace").strip()
        match = re.match(r"^(\d+)", output)
        if not match:
            return True
        size_kb = int(match.group(1))
        return size_kb <= heuristic_kb
    except Exception:
        return True


async def _list_tar_entries(tar_buffer: bytes) -> list[str]:
    tar_bin = "/usr/bin/tar" if platform.system() != "Windows" else "tar"
    try:
        proc = await asyncio.create_subprocess_exec(
            tar_bin, "-tzf", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout_data, _ = await asyncio.wait_for(
            proc.communicate(input=tar_buffer),
            timeout=10,
        )
        lines = stdout_data.decode("utf-8", errors="replace").split("\n")
        result = []
        for line in lines:
            normalized = line.replace("\\", "/")
            if normalized.startswith("./"):
                normalized = normalized[2:]
            normalized = normalized.rstrip("/")
            if normalized:
                result.append(normalized)
        return result
    except Exception:
        return []


async def _list_tree_entries(root_path: str, max_entries: int) -> list[str] | str:
    results: list[str] = []
    try:
        from openclaw.plugin_sdk.security_runtime import root
        root_handle = await root(root_path)

        async def visit(relative_dir: str) -> bool:
            entries = await root_handle.list(relative_dir, withFileTypes=True)
            if isinstance(entries, list):
                entries.sort(key=lambda e: e.get("name", ""))
            else:
                entries = []
            for entry in entries:
                rel = os.path.posix.join(relative_dir if relative_dir != "." else "", entry.get("name", ""))
                results.append(rel)
                if len(results) > max_entries:
                    return False
                if entry.get("isDirectory", False):
                    ok = await visit(rel)
                    if not ok:
                        return False
            return True

        success = await visit(".")
        return results if success else "TOO_MANY"
    except Exception:
        return results


async def handle_dir_fetch(params: DirFetchParams) -> DirFetchResult:
    requested_path = read_absolute_path(params.get("path"))
    if not isinstance(requested_path, str):
        return requested_path

    max_bytes = _clamp_max_bytes(params.get("maxBytes"))
    include_dotfiles = params.get("includeDotfiles") is True
    follow_symlinks = params.get("followSymlinks") is True
    preflight_only = params.get("preflightOnly") is True

    canonical = await resolve_canonical_read_path(
        requested_path,
        follow_symlinks,
        _classify_fs_error,
        "directory not found",
    )
    if not isinstance(canonical, str):
        return canonical

    directory = await stat_required_directory(canonical, _classify_fs_error)
    if not directory.get("ok"):
        return directory

    if preflight_only:
        try:
            entries = await _list_tree_entries(canonical, 5000)
            if entries == "TOO_MANY":
                return {
                    "ok": False,
                    "code": "TREE_TOO_LARGE",
                    "message": "directory tree exceeds 5000 entries during preflight",
                    "canonicalPath": canonical,
                }
            return {
                "ok": True,
                "path": canonical,
                "tarBase64": "",
                "tarBytes": 0,
                "sha256": "",
                "fileCount": len(entries),
                "entries": entries,
                "preflightOnly": True,
            }
        except Exception as err:
            code = _classify_fs_error(err)
            return {
                "ok": False,
                "code": code,
                "message": f"preflight readdir failed: {err}",
                "canonicalPath": canonical,
            }

    within_budget = await _preflight_du(canonical, max_bytes)
    if not within_budget:
        return {
            "ok": False,
            "code": "TREE_TOO_LARGE",
            "message": f"directory tree exceeds estimated size limit ({max_bytes} bytes raw)",
            "canonicalPath": canonical,
        }

    tar_bin = "/usr/bin/tar" if platform.system() != "Windows" else "tar"
    tar_args = ["-czf", "-", "-C", canonical, "."]

    TAR_HARD_TIMEOUT_MS = 60_000

    try:
        proc = await asyncio.create_subprocess_exec(
            tar_bin, *tar_args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        chunks: list[bytes] = []
        total_bytes = 0
        aborted = False

        async def _read_stream(stream, is_stdout=True):
            nonlocal total_bytes, aborted
            while not aborted:
                try:
                    chunk = await stream.read(65536)
                except Exception:
                    break
                if not chunk:
                    break
                if is_stdout:
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        aborted = True
                        proc.kill()
                        return "TOO_LARGE"
                    chunks.append(chunk)

        stdout_task = asyncio.create_task(_read_stream(proc.stdout, True))
        stderr_data = b""
        try:
            stderr_data = await asyncio.wait_for(proc.stderr.read(), timeout=TAR_HARD_TIMEOUT_MS / 1000)
        except asyncio.TimeoutError:
            pass

        await asyncio.wait_for(proc.wait(), timeout=TAR_HARD_TIMEOUT_MS / 1000)
        await stdout_task

        if aborted:
            return {
                "ok": False,
                "code": "TREE_TOO_LARGE",
                "message": f"tarball exceeded {max_bytes} byte limit mid-stream",
                "canonicalPath": canonical,
            }

        if proc.returncode != 0:
            stderr_text = stderr_data.decode("utf-8", errors="replace")
            return {
                "ok": False,
                "code": "READ_ERROR",
                "message": f"tar command exited {proc.returncode}: {stderr_text[:200]}",
                "canonicalPath": canonical,
            }

        tar_buffer = b"".join(chunks)
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "code": "READ_ERROR",
            "message": "tar command exceeded 60s wall-clock timeout (slow filesystem or symlink loop?)",
            "canonicalPath": canonical,
        }
    except Exception as err:
        return {
            "ok": False,
            "code": "READ_ERROR",
            "message": f"tar command failed: {err}",
            "canonicalPath": canonical,
        }

    sha256 = hashlib.sha256(tar_buffer).hexdigest()
    tar_base64 = base64.b64encode(tar_buffer).decode("ascii")
    tar_bytes = len(tar_buffer)
    entries = await _list_tar_entries(tar_buffer)

    return {
        "ok": True,
        "path": canonical,
        "tarBase64": tar_base64,
        "tarBytes": tar_bytes,
        "sha256": sha256,
        "fileCount": len(entries),
        "entries": entries,
    }