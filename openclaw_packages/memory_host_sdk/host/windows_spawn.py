from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List, Optional


def resolve_windows_spawn_program(
    command: str,
    platform: str = "",
    env: Optional[Dict[str, str]] = None,
    exec_path: str = "",
    package_name: str = "",
    allow_shell_fallback: bool = False,
) -> Dict[str, Any]:
    resolved = shutil.which(command)
    if resolved:
        return {
            "program": resolved,
            "args": [],
            "shell": False,
            "windowsHide": True,
        }
    if allow_shell_fallback:
        return {
            "program": command,
            "args": [],
            "shell": True,
            "windowsHide": True,
        }
    raise RuntimeError(f"Command not found: {command}")


def materialize_windows_spawn_program(program: Dict[str, Any], args: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "command": program.get("program", ""),
        "args": args or program.get("args", []),
        "shell": program.get("shell", False),
        "windowsHide": program.get("windowsHide", True),
    }
