from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Literal, TypedDict

MAX_CONTENT_BYTES = 16 * 1024 * 1024


class FileWriteParams(TypedDict, total=False):
    path: str
    contentBase64: str
    overwrite: bool
    createParents: bool
    expectedSha256: str
    followSymlinks: bool
    preflightOnly: bool


class FileWriteSuccess(TypedDict):
    ok: Literal[True]
    path: str
    size: int
    sha256: str
    overwritten: bool


class FileWriteError(TypedDict, total=False):
    ok: Literal[False]
    code: str
    message: str
    canonicalPath: str


FileWriteResult = FileWriteSuccess | FileWriteError


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _err(code: str, message: str, canonical_path: str | None = None) -> FileWriteError:
    result: FileWriteError = {"ok": False, "code": code, "message": message}
    if canonical_path is not None:
        result["canonicalPath"] = canonical_path
    return result


def _symlink_redirect_error(error: Any) -> FileWriteError:
    canonical_target = None
    cause = getattr(error, "cause", None)
    if cause and isinstance(cause, dict) and "canonicalPath" in cause:
        cp = cause["canonicalPath"]
        if isinstance(cp, str):
            canonical_target = cp
    return _err(
        "SYMLINK_REDIRECT",
        "path traverses a symlink; refusing because followSymlinks=false "
        "(set plugins.entries.file-transfer.config.nodes.<node>.followSymlinks=true to allow, "
        "or update allowWritePaths to the canonical path)",
        canonical_target,
    )


def _write_fs_safe_error(error: Any, target_path: str) -> FileWriteError:
    code = getattr(error, "code", None)
    if code == "symlink":
        return _err(
            "SYMLINK_TARGET_DENIED",
            f"path is a symlink; refusing to write through it: {target_path}",
        )
    if code == "not-file":
        return _err("IS_DIRECTORY", f"path resolves to a directory: {target_path}")
    if code == "already-exists":
        return _err("EXISTS_NO_OVERWRITE", f"file already exists and overwrite is false: {target_path}")
    return _err("WRITE_ERROR", str(error), target_path)


async def handle_file_write(params: dict[str, Any]) -> FileWriteResult:
    raw_path = params.get("path", "")
    if not isinstance(raw_path, str):
        raw_path = ""
    has_content_base64 = isinstance(params.get("contentBase64"), str)
    content_base64 = params.get("contentBase64", "") if has_content_base64 else ""
    overwrite = params.get("overwrite") is True
    create_parents = params.get("createParents") is True
    expected_sha256 = params.get("expectedSha256")
    if not isinstance(expected_sha256, str):
        expected_sha256 = None
    follow_symlinks = params.get("followSymlinks") is True
    preflight_only = params.get("preflightOnly") is True

    if not raw_path:
        return _err("INVALID_PATH", "path is required")
    if "\0" in raw_path:
        return _err("INVALID_PATH", "path must not contain NUL bytes")
    if not os.path.isabs(raw_path):
        return _err("INVALID_PATH", "path must be absolute")
    if not has_content_base64:
        return _err("INVALID_BASE64", "contentBase64 is required")

    try:
        buf = base64.b64decode(content_base64, validate=True)
    except Exception:
        return _err("INVALID_BASE64", "contentBase64 is not valid base64")

    if len(buf) > MAX_CONTENT_BYTES:
        return _err(
            "FILE_TOO_LARGE",
            f"decoded content is {len(buf)} bytes; maximum is {MAX_CONTENT_BYTES} bytes (16 MB)",
        )

    try:
        from openclaw.plugin_sdk.security_runtime import resolve_absolute_path_for_write
        resolved = await resolve_absolute_path_for_write(
            raw_path,
            symlinks="follow" if follow_symlinks else "reject",
        )
        target_path = resolved["path"]
        parent_dir = resolved["parentDir"]
        parent_exists = resolved["parentExists"]
    except Exception as error:
        code = getattr(error, "code", None)
        if code == "symlink":
            return _symlink_redirect_error(error)
        raise

    if not parent_exists:
        if not create_parents:
            return _err("PARENT_NOT_FOUND", f"parent directory does not exist: {parent_dir}")
        if preflight_only:
            computed_sha256 = _sha256_hex(buf)
            if expected_sha256 and expected_sha256.lower() != computed_sha256:
                return _err(
                    "INTEGRITY_FAILURE",
                    f"sha256 mismatch: expected {expected_sha256.lower()}, got {computed_sha256}",
                    target_path,
                )
            try:
                from openclaw.plugin_sdk.security_runtime import canonical_path_from_existing_ancestor
                canonical = await canonical_path_from_existing_ancestor(target_path)
            except Exception:
                canonical = target_path
            return {
                "ok": True,
                "path": canonical,
                "size": len(buf),
                "sha256": computed_sha256,
                "overwritten": False,
            }
        try:
            import aiofiles.os
            await aiofiles.os.makedirs(parent_dir, exist_ok=True)
        except Exception as mkdir_err:
            return _err("WRITE_ERROR", f"failed to create parent directories: {mkdir_err}")

    try:
        from openclaw.plugin_sdk.security_runtime import resolve_absolute_path_for_write
        await resolve_absolute_path_for_write(
            target_path,
            symlinks="follow" if follow_symlinks else "reject",
        )
    except Exception as error:
        code = getattr(error, "code", None)
        if code == "symlink":
            return _symlink_redirect_error(error)
        raise

    target_file_name = os.path.basename(target_path)
    overwritten = False
    try:
        import aiofiles
        existing_stat = await aiofiles.os.lstat(target_path)
        import stat as stat_module
        if stat_module.S_ISLNK(existing_stat.st_mode):
            return _err(
                "SYMLINK_TARGET_DENIED",
                f"path is a symlink; refusing to write through it: {target_path}",
            )
        if stat_module.S_ISDIR(existing_stat.st_mode):
            return _err("IS_DIRECTORY", f"path resolves to a directory: {target_path}")
        if not overwrite:
            return _err(
                "EXISTS_NO_OVERWRITE",
                f"file already exists and overwrite is false: {target_path}",
            )
        overwritten = True
    except FileNotFoundError:
        pass
    except Exception as stat_err:
        code = getattr(stat_err, "code", None)
        if code not in ("not-found", "ENOENT"):
            message = str(stat_err)
            if "permission" in message.lower():
                return _err("PERMISSION_DENIED", f"permission denied: {target_path}")
            return _err("WRITE_ERROR", f"unexpected stat error: {message}")

    computed_sha256 = _sha256_hex(buf)
    if expected_sha256 and expected_sha256.lower() != computed_sha256:
        return _err(
            "INTEGRITY_FAILURE",
            f"sha256 mismatch: expected {expected_sha256.lower()}, got {computed_sha256}",
            target_path,
        )

    if preflight_only:
        try:
            from openclaw.plugin_sdk.security_runtime import canonical_path_from_existing_ancestor
            canonical = await canonical_path_from_existing_ancestor(target_path)
        except Exception:
            canonical = target_path
        return {
            "ok": True,
            "path": canonical,
            "size": len(buf),
            "sha256": computed_sha256,
            "overwritten": overwritten,
        }

    try:
        from openclaw.plugin_sdk.security_runtime import root
        parent_root = await root(parent_dir)
        if overwrite:
            await parent_root.write(target_file_name, buf)
        else:
            await parent_root.create(target_file_name, buf)
    except Exception as write_err:
        code = getattr(write_err, "code", None)
        if code:
            return _write_fs_safe_error(write_err, target_path)
        message = str(write_err)
        if "permission" in message.lower() or "access" in message.lower():
            return _err("PERMISSION_DENIED", f"permission denied writing to: {parent_dir}")
        return _err("WRITE_ERROR", f"failed to write file: {message}")

    canonical_path = target_path
    try:
        from openclaw.plugin_sdk.security_runtime import root
        parent_root = await root(parent_dir)
        opened = await parent_root.open(target_file_name)
        canonical_path = opened.get("realPath", target_path)
        handle = opened.get("handle")
        if handle and hasattr(handle, "close"):
            try:
                await handle.close()
            except Exception:
                pass
    except Exception as open_err:
        code = getattr(open_err, "code", None)
        if code:
            return _write_fs_safe_error(open_err, target_path)

    return {
        "ok": True,
        "path": canonical_path,
        "size": len(buf),
        "sha256": computed_sha256,
        "overwritten": overwritten,
    }