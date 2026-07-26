"""Public SDK subpath for temporary file and workspace helpers."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

POSIX_OPENCLAW_TMP_DIR = "/tmp/openclaw"


class ResolvePreferredOpenClawTmpDirOptions(TypedDict, total=False):
    access_sync: Callable[[str, int], None]
    chmod_sync: Callable[[str, int], None]
    getuid: Callable[[], int | None]
    lstat_sync: Callable[[str], os.stat_result]
    mkdir_sync: Callable[[str, bool, int | None], None]
    platform: str
    tmpdir: Callable[[], str]
    warn: Callable[[str], None]


def resolve_preferred_openclaw_tmp_dir(
    options: ResolvePreferredOpenClawTmpDirOptions | None = None,
) -> str:
    """Resolve a safe OpenClaw temp root, falling back to user-scoped os temp paths when needed."""
    opts = options or {}
    access_mode = os.W_OK | os.X_OK
    access_sync = opts.get("access_sync") or os.access
    chmod_sync = opts.get("chmod_sync") or os.chmod
    lstat_sync = opts.get("lstat_sync") or os.lstat
    mkdir_sync = opts.get("mkdir_sync") or _mkdir_sync
    warn = opts.get("warn") or (lambda message: print(message, file=sys.stderr))
    getuid = opts.get("getuid") or (lambda: os.getuid() if hasattr(os, "getuid") else None)
    tmpdir = opts.get("tmpdir") or tempfile.gettempdir
    platform = opts.get("platform") or sys.platform
    uid = getuid()

    def is_secure_dir_for_user(st: os.stat_result) -> bool:
        if uid is None:
            return True
        if hasattr(st, "st_uid") and st.st_uid != uid:
            return False
        return (st.st_mode & 0o022) == 0

    def fallback() -> str:
        suffix = "openclaw" if uid is None else f"openclaw-{uid}"
        return str(Path(tmpdir()) / suffix)

    def is_trusted_tmp_dir(st: os.stat_result) -> bool:
        return (
            stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode) and is_secure_dir_for_user(st)
        )

    def resolve_dir_state(candidate_path: str) -> str:
        try:
            candidate = lstat_sync(candidate_path)
            if not is_trusted_tmp_dir(candidate):
                return "invalid"
            if not access_sync(candidate_path, access_mode):
                return "invalid"
            return "available"
        except OSError as err:
            return "missing" if isinstance(err, FileNotFoundError) else "invalid"

    def try_repair_writable_bits(candidate_path: str) -> bool:
        try:
            st = lstat_sync(candidate_path)
            if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
                return False
            if uid is not None and hasattr(st, "st_uid") and st.st_uid != uid:
                return False
            if (st.st_mode & 0o022) == 0:
                return resolve_dir_state(candidate_path) == "available"
            try:
                chmod_sync(candidate_path, 0o700)
            except OSError as chmod_err:
                if isinstance(chmod_err, (PermissionError, FileNotFoundError)):
                    return resolve_dir_state(candidate_path) == "available"
                raise
            warn(f"[openclaw] tightened permissions on temp dir: {candidate_path}")
            return resolve_dir_state(candidate_path) == "available"
        except OSError:
            return False

    def ensure_trusted_fallback_dir() -> str:
        fallback_path = fallback()
        state = resolve_dir_state(fallback_path)
        if state == "available":
            return fallback_path
        if state == "invalid":
            if try_repair_writable_bits(fallback_path):
                return fallback_path
            raise OSError(f"Unsafe fallback OpenClaw temp dir: {fallback_path}")
        try:
            mkdir_sync(fallback_path, True, 0o700)
            chmod_sync(fallback_path, 0o700)
        except OSError as err:
            raise OSError(f"Unable to create fallback OpenClaw temp dir: {fallback_path}") from err
        if resolve_dir_state(fallback_path) != "available" and not try_repair_writable_bits(
            fallback_path
        ):
            raise OSError(f"Unsafe fallback OpenClaw temp dir: {fallback_path}")
        return fallback_path

    if platform == "win32":
        return ensure_trusted_fallback_dir()

    preferred_dir = POSIX_OPENCLAW_TMP_DIR
    preferred_state = resolve_dir_state(preferred_dir)
    if preferred_state == "available":
        return preferred_dir
    if preferred_state == "invalid":
        if try_repair_writable_bits(preferred_dir):
            return preferred_dir
        return ensure_trusted_fallback_dir()

    try:
        if not access_sync(str(Path(preferred_dir).parent), access_mode):
            return ensure_trusted_fallback_dir()
        mkdir_sync(preferred_dir, True, 0o700)
        chmod_sync(preferred_dir, 0o700)
        if resolve_dir_state(preferred_dir) != "available" and not try_repair_writable_bits(
            preferred_dir
        ):
            return ensure_trusted_fallback_dir()
        return preferred_dir
    except OSError:
        return ensure_trusted_fallback_dir()


def _mkdir_sync(path: str, recursive: bool, mode: int | None) -> None:
    Path(path).mkdir(parents=recursive, mode=mode, exist_ok=True)


__all__ = ["POSIX_OPENCLAW_TMP_DIR", "resolve_preferred_openclaw_tmp_dir"]
