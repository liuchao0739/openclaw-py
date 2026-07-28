from __future__ import annotations

import asyncio
import os
import shutil
import stat
import subprocess
import tempfile
import time
import uuid as _uuid
from typing import Any

from ..harness_types import (
    ExecutionError,
    ExecutionEnvExecOptions,
    FileError,
    FileInfo,
)
from .kill_tree import kill_process_tree

MAX_TIMER_TIMEOUT_MS = 2_147_000_000


def _resolve_path(cwd: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(cwd, path)


def resolve_exec_timeout_ms(timeout_seconds: Any) -> int | None:
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        return None
    milliseconds = int(timeout_seconds * 1000)
    if milliseconds <= 0:
        return 1
    return min(milliseconds, MAX_TIMER_TIMEOUT_MS)


def _file_info_from_stats(
    path: str,
    stats: os.stat_result,
) -> dict[str, Any]:
    if stat.S_ISREG(stats.st_mode):
        kind = "file"
    elif stat.S_ISDIR(stats.st_mode):
        kind = "directory"
    elif stat.S_ISLNK(stats.st_mode):
        kind = "symlink"
    else:
        return {"ok": False, "error": FileError("invalid", "Unsupported file type", path)}
    return {
        "ok": True,
        "value": FileInfo(
            name=os.path.basename(path.rstrip("/") or path),
            path=path,
            kind=kind,
            size=stats.st_size,
            mtimeMs=stats.st_mtime * 1000,
        ),
    }


def _to_file_error(error: Any, path: str | None = None) -> FileError:
    if isinstance(error, FileError):
        return error
    msg = str(error)
    code = "unknown"
    if isinstance(error, FileNotFoundError):
        code = "not_found"
    elif isinstance(error, PermissionError):
        code = "permission_denied"
    elif isinstance(error, NotADirectoryError):
        code = "not_directory"
    elif isinstance(error, IsADirectoryError):
        code = "is_directory"
    elif isinstance(error, ValueError):
        code = "invalid"
    return FileError(code, msg, path)


def _abort_result(signal: Any, path: str | None = None) -> dict[str, Any] | None:
    if signal is not None and getattr(signal, "aborted", False):
        return {"ok": False, "error": FileError("aborted", "aborted", path)}
    return None


async def _path_exists(path: str) -> bool:
    return os.path.exists(path)


async def _get_shell_config(
    custom_shell_path: str | None = None,
) -> dict[str, Any]:
    if custom_shell_path:
        if await _path_exists(custom_shell_path):
            return {"ok": True, "value": {"shell": custom_shell_path, "args": ["-c"]}}
        return {
            "ok": False,
            "error": ExecutionError(
                "shell_unavailable",
                f"Custom shell path not found: {custom_shell_path}",
            ),
        }
    if os.name == "nt":
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return {"ok": True, "value": {"shell": candidate, "args": ["-c"]}}
        return {
            "ok": False,
            "error": ExecutionError("shell_unavailable", "No bash shell found"),
        }
    if os.path.exists("/bin/bash"):
        return {"ok": True, "value": {"shell": "/bin/bash", "args": ["-c"]}}
    return {"ok": True, "value": {"shell": "sh", "args": ["-c"]}}


class NodeExecutionEnv:
    def __init__(self, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        self.cwd: str = options.get("cwd", os.getcwd())
        self._shell_path: str | None = options.get("shellPath")
        self._shell_env: dict[str, str] | None = options.get("shellEnv")

    async def absolute_path(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        return {"ok": True, "value": _resolve_path(self.cwd, path)}

    async def join_path(
        self, parts: list[str], abort_signal: Any | None = None
    ) -> dict[str, Any]:
        return {"ok": True, "value": os.path.join(*parts) if parts else ""}

    async def exec(
        self,
        command: str,
        options: ExecutionEnvExecOptions | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        abort_signal = options.abortSignal
        if abort_signal is not None and getattr(abort_signal, "aborted", False):
            return {"ok": False, "error": ExecutionError("aborted", "aborted")}

        cwd = _resolve_path(self.cwd, options.cwd) if options.cwd else self.cwd
        shell_config = await _get_shell_config(self._shell_path)
        if not shell_config.get("ok"):
            return shell_config

        shell = shell_config["value"]["shell"]
        shell_args = shell_config["value"]["args"]
        timeout_ms = resolve_exec_timeout_ms(options.timeout)

        env = dict(os.environ)
        if self._shell_env:
            env.update(self._shell_env)
        if options.env:
            env.update(options.env)

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                shell,
                *shell_args,
                command,
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as error:
            return {
                "ok": False,
                "error": ExecutionError("spawn_error", str(error), error),
            }

        async def _read_stream(stream: Any, parts: list[str], on_data: Any) -> None:
            if stream is None:
                return
            while True:
                try:
                    line = await stream.read(4096)
                except Exception:
                    break
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                parts.append(text)
                if on_data is not None:
                    try:
                        on_data(text)
                    except Exception:
                        pass

        stdout_task = asyncio.create_task(
            _read_stream(proc.stdout, stdout_parts, options.onStdout)
        )
        stderr_task = asyncio.create_task(
            _read_stream(proc.stderr, stderr_parts, options.onStderr)
        )

        try:
            if timeout_ms is not None:
                await asyncio.wait_for(proc.wait(), timeout=timeout_ms / 1000.0)
            else:
                await proc.wait()
        except asyncio.TimeoutError:
            if proc.pid is not None:
                kill_process_tree(proc.pid, {"force": True})
            await stdout_task
            await stderr_task
            return {
                "ok": False,
                "error": ExecutionError("timeout", f"timeout:{options.timeout}"),
            }

        await stdout_task
        await stderr_task

        if abort_signal is not None and getattr(abort_signal, "aborted", False):
            return {"ok": False, "error": ExecutionError("aborted", "aborted")}

        return {
            "ok": True,
            "value": {
                "stdout": "".join(stdout_parts),
                "stderr": "".join(stderr_parts),
                "exitCode": proc.returncode or 0,
            },
        }

    async def read_text_file(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        aborted = _abort_result(abort_signal, resolved)
        if aborted:
            return aborted
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()
            return {"ok": True, "value": content}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def read_text_lines(
        self,
        path: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        resolved = _resolve_path(self.cwd, path)
        aborted = _abort_result(options.get("abortSignal"), resolved)
        if aborted:
            return aborted
        max_lines = options.get("maxLines")
        if max_lines is not None and max_lines <= 0:
            return {"ok": True, "value": []}
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                lines: list[str] = []
                for line in f:
                    if options.get("abortSignal") and getattr(options["abortSignal"], "aborted", False):
                        return _abort_result(options["abortSignal"], resolved) or {
                            "ok": True,
                            "value": lines,
                        }
                    lines.append(line.rstrip("\n"))
                    if max_lines is not None and len(lines) >= max_lines:
                        break
                return {"ok": True, "value": lines}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def read_binary_file(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        aborted = _abort_result(abort_signal, resolved)
        if aborted:
            return aborted
        try:
            with open(resolved, "rb") as f:
                content = f.read()
            return {"ok": True, "value": content}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def write_file(
        self,
        path: str,
        content: str | bytes,
        abort_signal: Any | None = None,
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        aborted = _abort_result(abort_signal, resolved)
        if aborted:
            return aborted
        try:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            mode = "w" if isinstance(content, str) else "wb"
            with open(resolved, mode) as f:
                f.write(content)
            return {"ok": True, "value": None}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def append_file(
        self,
        path: str,
        content: str | bytes,
        abort_signal: Any | None = None,
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        try:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            mode = "a" if isinstance(content, str) else "ab"
            with open(resolved, mode) as f:
                f.write(content)
            return {"ok": True, "value": None}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def file_info(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        try:
            stats = os.lstat(resolved)
            return _file_info_from_stats(resolved, stats)
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def list_dir(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        aborted = _abort_result(abort_signal, resolved)
        if aborted:
            return aborted
        try:
            entries = os.listdir(resolved)
            infos: list[FileInfo] = []
            for entry in entries:
                entry_path = os.path.join(resolved, entry)
                try:
                    stats = os.lstat(entry_path)
                    info = _file_info_from_stats(entry_path, stats)
                    if info.get("ok"):
                        infos.append(info["value"])
                except Exception as error:
                    return {"ok": False, "error": _to_file_error(error, entry_path)}
            return {"ok": True, "value": infos}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def canonical_path(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        resolved = _resolve_path(self.cwd, path)
        try:
            return {"ok": True, "value": os.path.realpath(resolved)}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def exists(
        self, path: str, abort_signal: Any | None = None
    ) -> dict[str, Any]:
        result = await self.file_info(path, abort_signal)
        if result.get("ok"):
            return {"ok": True, "value": True}
        if result["error"].code == "not_found":
            return {"ok": True, "value": False}
        return result

    async def create_dir(
        self,
        path: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        resolved = _resolve_path(self.cwd, path)
        try:
            os.makedirs(resolved, exist_ok=options.get("recursive", True))
            return {"ok": True, "value": None}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def remove(
        self,
        path: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        resolved = _resolve_path(self.cwd, path)
        try:
            if os.path.isdir(resolved) and not os.path.islink(resolved):
                if options.get("recursive", False):
                    shutil.rmtree(resolved)
                else:
                    os.rmdir(resolved)
            else:
                os.unlink(resolved)
            return {"ok": True, "value": None}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error, resolved)}

    async def create_temp_dir(
        self,
        prefix: str = "tmp-",
        abort_signal: Any | None = None,
    ) -> dict[str, Any]:
        try:
            return {"ok": True, "value": tempfile.mkdtemp(prefix=prefix)}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error)}

    async def create_temp_file(
        self, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        options = options or {}
        dir_result = await self.create_temp_dir("tmp-")
        if not dir_result.get("ok"):
            return dir_result
        dir_path = dir_result["value"]
        file_path = os.path.join(
            dir_path,
            f"{options.get('prefix', '')}{_uuid.uuid4().hex}{options.get('suffix', '')}",
        )
        try:
            with open(file_path, "w") as f:
                pass
            return {"ok": True, "value": file_path}
        except Exception as error:
            return {"ok": False, "error": _to_file_error(error)}

    async def cleanup(self) -> None:
        pass
