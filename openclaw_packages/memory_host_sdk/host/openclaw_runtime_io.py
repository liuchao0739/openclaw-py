from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable, List, Optional

CHARS_PER_TOKEN_ESTIMATE = 4
DEFAULT_SQLITE_WAL_AUTOCHECKPOINT_PAGES = 1000
DEFAULT_SQLITE_WAL_CHECKPOINT_INTERVAL_MS = 60_000
DEFAULT_SQLITE_WAL_TRUNCATE_INTERVAL_MS = 3_600_000


class _Root:
    def __init__(self, base: str):
        self._base = base

    def resolve(self, rel_path: str) -> str:
        abs_path = os.path.join(self._base, rel_path)
        real = os.path.realpath(abs_path)
        if not real.startswith(self._base):
            raise ValueError(f"Path escapes root: {rel_path}")
        return real


def root(base_dir: str) -> _Root:
    return _Root(base_dir)


def create_subsystem_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def detect_mime(buffer: bytes, file_path: str) -> Optional[str]:
    import mimetypes
    mime, _ = mimetypes.guess_type(file_path)
    return mime


def estimate_string_chars(text: str) -> int:
    return len(text)


def run_tasks_with_concurrency(tasks: list, limit: int, error_mode: str = "stop") -> dict:
    import asyncio
    sem = asyncio.Semaphore(limit)
    results = []
    first_error = None
    has_error = False

    async def run_task(task):
        nonlocal first_error, has_error
        async with sem:
            try:
                if asyncio.iscoroutinefunction(task):
                    return await task()
                return task()
            except Exception as e:
                if not has_error:
                    first_error = e
                    has_error = True
                if error_mode == "stop":
                    raise
                return None

    async def _run_all():
        coros = [run_task(t) for t in tasks]
        for coro in coros:
            try:
                results.append(await coro)
            except Exception:
                pass

    asyncio.run(_run_all())
    return {"results": results, "firstError": first_error, "hasError": has_error}


def shorten_home_in_string(path_str: str) -> str:
    home = os.path.expanduser("~")
    if path_str.startswith(home):
        return "~" + path_str[len(home):]
    return path_str


def shorten_home_path(path_str: str) -> str:
    return shorten_home_in_string(path_str)


def resolve_user_path(input_path: str) -> str:
    from .config_utils import resolve_user_path as _resolve
    return _resolve(input_path)


def split_shell_args(command: str) -> Optional[list]:
    import shlex
    try:
        return shlex.split(command)
    except ValueError:
        return None


def truncate_utf16_safe(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    result = text[:max_chars]
    if result and ord(result[-1]) >= 0xd800 and ord(result[-1]) <= 0xdbff:
        result = result[:-1]
    return result


def resolve_global_singleton(key: str, factory: Callable) -> Any:
    global _singletons
    if key not in _singletons:
        _singletons[key] = factory()
    return _singletons[key]


_singletons = {}


def install_process_warning_filter() -> None:
    import warnings
    warnings.filterwarnings("ignore")


def should_ignore_warning(warning: object) -> bool:
    return False


def redact_sensitive_text(text: str, mode: str = "tools") -> str:
    from .error_utils import redact_sensitive_text as _redact
    return _redact(text)


def apply_windows_spawn_program_policy(program: dict) -> dict:
    return program


def materialize_windows_spawn_program(program: dict) -> dict:
    return program


def resolve_windows_executable_path(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)


def resolve_windows_spawn_program(name: str) -> Optional[dict]:
    path = resolve_windows_executable_path(name)
    if path:
        return {"program": path}
    return None


def resolve_windows_spawn_program_candidate(name: str) -> Optional[dict]:
    return resolve_windows_spawn_program(name)
