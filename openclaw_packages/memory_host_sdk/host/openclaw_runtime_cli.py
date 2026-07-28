from __future__ import annotations

import sys
from typing import Any, Callable, Optional

_verbose = False


def format_error_message(err: object) -> str:
    from .error_utils import format_error_message as _format
    return _format(err)


def format_help_examples(examples: list) -> str:
    lines = []
    for ex in examples:
        if isinstance(ex, dict):
            lines.append(f"  {ex.get('cmd', '')} - {ex.get('desc', '')}")
        else:
            lines.append(f"  {ex}")
    return "\n".join(lines)


def resolve_command_secret_refs_via_gateway(command: str) -> list:
    return []


def with_progress(title: str) -> Any:
    return _ProgressContext(title)


def with_progress_totals(title: str, total: int) -> Any:
    return _ProgressTotalsContext(title, total)


class _ProgressContext:
    def __init__(self, title: str):
        self.title = title

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, message: str) -> None:
        pass


class _ProgressTotalsContext:
    def __init__(self, title: str, total: int):
        self.title = title
        self.total = total

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, completed: int, message: str = "") -> None:
        pass


def with_manager(fn: Callable) -> Callable:
    return fn


class _DefaultRuntime:
    def __init__(self):
        self.name = "default"


default_runtime = _DefaultRuntime()


def format_docs_link(path: str) -> str:
    return f"https://docs.openclaw.ai{path}"


def colorize(text: str, color: str = "") -> str:
    return text


def is_rich() -> bool:
    return True


theme = {
    "primary": "",
    "secondary": "",
}


def is_verbose() -> bool:
    return _verbose


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def shorten_home_in_string(path_str: str) -> str:
    from .openclaw_runtime_io import shorten_home_in_string as _shorten
    return _shorten(path_str)


def shorten_home_path(path_str: str) -> str:
    return shorten_home_in_string(path_str)
