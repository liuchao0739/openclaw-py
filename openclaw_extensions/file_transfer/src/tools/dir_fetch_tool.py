from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import platform
import stat as stat_module
import time
from typing import Any

from openclaw_extensions.file_transfer.shared.audit import append_file_transfer_audit
from openclaw_extensions.file_transfer.shared.mime import (
    IMAGE_MIME_INLINE_SET,
    mime_from_extension,
)
from openclaw_extensions.file_transfer.shared.params import human_size, read_boolean, read_clamped_int
from openclaw_extensions.file_transfer.src.tools.descriptors import (
    DIR_FETCH_DEFAULT_MAX_BYTES,
    DIR_FETCH_HARD_MAX_BYTES,
    DIR_FETCH_TOOL_DESCRIPTOR,
    FILE_TRANSFER_SUBDIR,
)
from openclaw_extensions.file_transfer.src.tools.node_tool_invoke import (
    invoke_node_tool_payload,
    read_required_node_path,
)

MEDIA_URL_CAP = 25
TAR_UNPACK_TIMEOUT_MS = 60_000
TAR_UNPACK_MAX_ENTRIES = 5000
TAR_LIST_OUTPUT_MAX_CHARS = 32 * 1024 * 1024
TAR_STDERR_TAIL_CHARS = 4096
DIR_FETCH_MAX_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
DIR_FETCH_MAX_SINGLE_FILE_BYTES = 16 * 1024 * 1024


def _append_bounded_text_tail(current: str, text: str, max_chars: int) -> str:
    next_text = current + text
    return next_text[-max_chars:] if len(next_text) > max_chars else next_text


async def _list_tar_output_lines(
    args: list[str],
    label: str,
    tar_buffer: bytes,
    map_line: Any,
    max_values: int,
) -> dict[str, Any]:
    tar_bin = "/usr/bin/tar" if platform.system() != "Windows" else "tar"
    try:
        proc = await asyncio.create_subprocess_exec(
            tar_bin, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        values: list[Any] = []
        pending = b""
        output_chars = 0
        stderr_text = ""

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(input=tar_buffer),
                timeout=30,
            )
            stderr_text = stderr_data.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "reason": f"{label} timed out"}

        lines_data = (pending + stdout_data).split(b"\n")
        pending = lines_data.pop() if lines_data else b""
        for line_bytes in lines_data:
            line = line_bytes.decode("utf-8", errors="replace")
            if not line:
                continue
            mapped = map_line(line)
            values.append(mapped)
            if len(values) >= max_values:
                return {"ok": True, "values": values}

        if pending:
            line = pending.decode("utf-8", errors="replace")
            if line:
                mapped = map_line(line)
                values.append(mapped)

        if proc.returncode != 0:
            return {"ok": False, "reason": f"{label} exited {proc.returncode}: {stderr_text[-200:]}"}

        return {"ok": True, "values": values}
    except Exception as e:
        return {"ok": False, "reason": f"{label} error: {e}"}


async def _compute_file_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    try:
        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()


async def _list_tar_paths(tar_buffer: bytes) -> dict[str, Any]:
    result = await _list_tar_output_lines(
        args=["-tzf", "-"],
        label="tar -tzf",
        tar_buffer=tar_buffer,
        map_line=lambda line: line,
        max_values=TAR_UNPACK_MAX_ENTRIES + 1,
    )
    if result.get("ok"):
        return {"ok": True, "paths": result["values"]}
    return result


async def _list_tar_type_chars(tar_buffer: bytes) -> dict[str, Any]:
    result = await _list_tar_output_lines(
        args=["-tzvf", "-"],
        label="tar -tzvf",
        tar_buffer=tar_buffer,
        map_line=lambda line: line[0] if line else "",
        max_values=TAR_UNPACK_MAX_ENTRIES + 1,
    )
    if result.get("ok"):
        return {"ok": True, "typeChars": result["values"]}
    return result


async def _pre_validate_tarball(tar_buffer: bytes) -> dict[str, Any]:
    names_result = await _list_tar_paths(tar_buffer)
    if not names_result.get("ok"):
        return names_result
    paths = names_result["paths"]

    if len(paths) > TAR_UNPACK_MAX_ENTRIES:
        return {
            "ok": False,
            "reason": f"archive contains {len(paths)} entries; limit {TAR_UNPACK_MAX_ENTRIES}",
        }

    types_result = await _list_tar_type_chars(tar_buffer)
    if not types_result.get("ok"):
        return types_result
    type_chars = types_result["typeChars"]

    if len(type_chars) != len(paths):
        return {
            "ok": False,
            "reason": f"tar -tzf and tar -tzvf disagree on entry count ({len(paths)} vs {len(type_chars)}); refusing",
        }

    for i in range(len(paths)):
        entry_path = paths[i]
        t = type_chars[i] if i < len(type_chars) else ""
        if t in ("l", "h"):
            return {"ok": False, "reason": f"archive contains link entry: {entry_path}"}
        if t not in ("-", "d"):
            return {"ok": False, "reason": f"archive contains non-regular entry type '{t}': {entry_path}"}
        if os.path.isabs(entry_path):
            return {"ok": False, "reason": f"archive contains absolute path: {entry_path}"}
        norm = os.path.normpath(entry_path)
        if norm == ".." or norm.startswith("../") or "/../" in norm:
            return {"ok": False, "reason": f"archive contains '..' traversal: {entry_path}"}
        if "\\" in entry_path:
            return {"ok": False, "reason": f"archive contains backslash in path: {entry_path}"}

    return {"ok": True}


async def _validate_tar_uncompressed_budget(
    tar_buffer: bytes,
    max_bytes: int = DIR_FETCH_MAX_UNCOMPRESSED_BYTES,
) -> dict[str, Any]:
    tar_bin = "/usr/bin/tar" if platform.system() != "Windows" else "tar"
    try:
        proc = await asyncio.create_subprocess_exec(
            tar_bin, "-xOzf", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        total_bytes = 0
        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(input=tar_buffer),
                timeout=TAR_UNPACK_TIMEOUT_MS / 1000,
            )
            total_bytes = len(stdout_data)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "reason": "tar uncompressed budget validation timed out"}

        if total_bytes > max_bytes:
            return {
                "ok": False,
                "reason": f"archive expands past uncompressed budget {max_bytes} bytes",
            }

        if proc.returncode != 0:
            return {
                "ok": False,
                "reason": f"tar uncompressed budget validation exited {proc.returncode}",
            }

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": f"tar uncompressed budget validation error: {e}"}


async def _unpack_tar(tar_buffer: bytes, dest_dir: str) -> None:
    import aiofiles.os
    await aiofiles.os.makedirs(dest_dir, exist_ok=True)

    tar_bin = "/usr/bin/tar" if platform.system() != "Windows" else "tar"
    proc = await asyncio.create_subprocess_exec(
        tar_bin, "-xzf", "-", "-C", dest_dir, "--no-same-owner", "--no-same-permissions",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        await asyncio.wait_for(proc.communicate(input=tar_buffer), timeout=TAR_UNPACK_TIMEOUT_MS / 1000)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"tar unpack timed out after {TAR_UNPACK_TIMEOUT_MS}ms")

    if proc.returncode != 0:
        raise RuntimeError(f"tar unpack exited {proc.returncode}")


async def _walk_dir(dir_path: str, root_dir: str) -> list[dict[str, str]]:
    import aiofiles
    entries = await aiofiles.os.scandir(dir_path)
    results: list[dict[str, str]] = []
    async for entry in entries:
        abs_path = os.path.join(dir_path, entry.name)
        is_dir = await entry.is_dir(follow_symlinks=False)
        is_file = await entry.is_file(follow_symlinks=False)
        if is_dir:
            nested = await _walk_dir(abs_path, root_dir)
            results.extend(nested)
        elif is_file:
            rel_path = os.path.relpath(abs_path, root_dir)
            results.append({"relPath": rel_path, "absPath": abs_path})
    return results


async def create_dir_fetch_tool() -> dict:
    descriptor = dict(DIR_FETCH_TOOL_DESCRIPTOR)

    async def _execute(tool_call_id: str, args: dict) -> dict:
        node, dir_path = read_required_node_path(args)

        max_bytes = read_clamped_int(
            input_dict=args,
            key="maxBytes",
            default_value=DIR_FETCH_DEFAULT_MAX_BYTES,
            hard_min=1,
            hard_max=DIR_FETCH_HARD_MAX_BYTES,
        )
        include_dotfiles = read_boolean(args, "includeDotfiles", False)

        node_id, node_display_name, payload, started_at = await invoke_node_tool_payload(
            node=node,
            params=args,
            command="dir.fetch",
            command_params={
                "path": dir_path,
                "maxBytes": max_bytes,
                "includeDotfiles": include_dotfiles,
            },
            requested_path=dir_path,
        )

        canonical_path = payload.get("path", "")
        tar_base64 = payload.get("tarBase64", "")
        tar_bytes = payload.get("tarBytes", -1)
        sha256 = payload.get("sha256", "")
        file_count = payload.get("fileCount", 0)

        if not canonical_path or not tar_base64 or tar_bytes < 0 or not sha256:
            raise ValueError("invalid dir.fetch payload (missing fields)")

        tar_buffer = base64.b64decode(tar_base64)
        if len(tar_buffer) != tar_bytes:
            raise ValueError(
                f"dir.fetch size mismatch: payload says {tar_bytes} bytes, decoded {len(tar_buffer)}"
            )

        local_sha256 = hashlib.sha256(tar_buffer).hexdigest()
        if local_sha256 != sha256:
            raise ValueError("dir.fetch sha256 mismatch (integrity failure)")

        validation = await _pre_validate_tarball(tar_buffer)
        if not validation.get("ok"):
            await append_file_transfer_audit(
                {
                    "op": "dir.fetch",
                    "nodeId": node_id,
                    "nodeDisplayName": node_display_name,
                    "requestedPath": dir_path,
                    "canonicalPath": canonical_path,
                    "decision": "error",
                    "errorCode": "UNSAFE_ARCHIVE",
                    "errorMessage": validation.get("reason", ""),
                    "sizeBytes": tar_bytes,
                    "sha256": sha256,
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            raise ValueError(f"dir.fetch UNSAFE_ARCHIVE: {validation.get('reason', '')}")

        budget = await _validate_tar_uncompressed_budget(tar_buffer)
        if not budget.get("ok"):
            await append_file_transfer_audit(
                {
                    "op": "dir.fetch",
                    "nodeId": node_id,
                    "nodeDisplayName": node_display_name,
                    "requestedPath": dir_path,
                    "canonicalPath": canonical_path,
                    "decision": "error",
                    "errorCode": "TREE_TOO_LARGE",
                    "errorMessage": budget.get("reason", ""),
                    "sizeBytes": tar_bytes,
                    "sha256": sha256,
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            raise ValueError(f"dir.fetch UNCOMPRESSED_TOO_LARGE: {budget.get('reason', '')}")

        from openclaw.plugin_sdk.media_store import save_media_buffer
        saved_tar = await save_media_buffer(
            tar_buffer,
            "application/gzip",
            FILE_TRANSFER_SUBDIR,
            DIR_FETCH_HARD_MAX_BYTES,
        )

        tar_dir = os.path.dirname(saved_tar.get("path", ""))
        tar_base_name = os.path.basename(saved_tar.get("path", ""))
        unpack_id = f"dir-fetch-{tar_base_name}"
        root_dir = os.path.join(tar_dir, unpack_id)

        await _unpack_tar(tar_buffer, root_dir)

        walked = await _walk_dir(root_dir, root_dir)
        files: list[dict] = []
        total_uncompressed = 0

        async def _abort_and_cleanup(reason: str) -> None:
            import shutil
            try:
                shutil.rmtree(root_dir, ignore_errors=True)
            except Exception:
                pass
            await append_file_transfer_audit(
                {
                    "op": "dir.fetch",
                    "nodeId": node_id,
                    "nodeDisplayName": node_display_name,
                    "requestedPath": dir_path,
                    "canonicalPath": canonical_path,
                    "decision": "error",
                    "errorCode": "TREE_TOO_LARGE",
                    "errorMessage": reason,
                    "sizeBytes": tar_bytes,
                    "sha256": sha256,
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            raise ValueError(f"dir.fetch UNCOMPRESSED_TOO_LARGE: {reason}")

        for entry in walked:
            rel_path = entry["relPath"]
            abs_path = entry["absPath"]
            try:
                import aiofiles
                st = await aiofiles.os.stat(abs_path)
                size = st.st_size
            except Exception:
                continue

            if size > DIR_FETCH_MAX_SINGLE_FILE_BYTES:
                await _abort_and_cleanup(
                    f"extracted file {rel_path} is {size} bytes (limit {DIR_FETCH_MAX_SINGLE_FILE_BYTES})"
                )

            total_uncompressed += size
            if total_uncompressed > DIR_FETCH_MAX_UNCOMPRESSED_BYTES:
                await _abort_and_cleanup(
                    f"extracted tree exceeds uncompressed budget {DIR_FETCH_MAX_UNCOMPRESSED_BYTES} bytes (decompression bomb?)"
                )

            mime_type = mime_from_extension(rel_path)
            file_sha256 = await _compute_file_sha256(abs_path)
            files.append({
                "relPath": rel_path,
                "size": size,
                "mimeType": mime_type,
                "sha256": file_sha256,
                "localPath": abs_path,
            })

        image_files = [f for f in files if f["mimeType"] in IMAGE_MIME_INLINE_SET]
        non_image_files = [f for f in files if f["mimeType"] not in IMAGE_MIME_INLINE_SET]
        all_ordered = image_files + non_image_files
        dropped_from_media = max(0, len(all_ordered) - MEDIA_URL_CAP)
        media_urls = [f["localPath"] for f in all_ordered[:MEDIA_URL_CAP]]

        short_hash = sha256[:12]
        media_note = (
            f" (channel attaches first {MEDIA_URL_CAP}; {dropped_from_media} more in details.files)"
            if dropped_from_media
            else ""
        )
        summary_text = (
            f"Fetched {file_count} files from {canonical_path} "
            f"({human_size(tar_bytes)} compressed, sha256:{short_hash}) "
            f"— saved on the gateway under {root_dir}/{media_note}"
        )

        await append_file_transfer_audit(
            {
                "op": "dir.fetch",
                "nodeId": node_id,
                "nodeDisplayName": node_display_name,
                "requestedPath": dir_path,
                "canonicalPath": canonical_path,
                "decision": "allowed",
                "sizeBytes": tar_bytes,
                "sha256": sha256,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )

        return {
            "content": [{"type": "text", "text": summary_text}],
            "details": {
                "path": canonical_path,
                "rootDir": root_dir,
                "fileCount": file_count,
                "tarBytes": tar_bytes,
                "sha256": sha256,
                "files": files,
                "media": {"mediaUrls": media_urls},
            },
        }

    descriptor["execute"] = _execute
    descriptor["testing"] = {
        "preValidateTarball": _pre_validate_tarball,
        "validateTarUncompressedBudget": _validate_tar_uncompressed_budget,
    }
    return descriptor