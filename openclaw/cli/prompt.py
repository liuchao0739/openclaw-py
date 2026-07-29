from __future__ import annotations

import getpass
import sys
from typing import Any


def prompt(message: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        result = input(f"{message}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default or ""
    return result or default or ""


def prompt_password(message: str = "Password") -> str:
    try:
        return getpass.getpass(f"{message}: ")
    except (EOFError, KeyboardInterrupt):
        return ""


def confirm(message: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        result = input(f"{message} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not result:
        return default
    return result in ("y", "yes")


def select(message: str, options: list[str], default: int = 0) -> int:
    print(message)
    for i, opt in enumerate(options):
        marker = "*" if i == default else " "
        print(f"  {marker} {i + 1}. {opt}")
    try:
        result = input(f"Select [1-{len(options)}] (default {default + 1}): ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    if not result:
        return default
    try:
        idx = int(result) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    return default
