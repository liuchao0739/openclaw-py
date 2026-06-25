"""Tool binary manager for agent-side helper commands.

Locates or downloads pinned helper binaries such as fd and ripgrep.
This port provides path resolution; the download logic is deferred.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Literal

ToolName = Literal["fd", "rg"]

_TOOL_CONFIGS: dict[str, dict[str, Any]] = {
    "fd": {
        "name": "fd",
        "binaryName": "fd",
        "systemBinaryNames": ["fd", "fdfind"],
    },
    "rg": {
        "name": "ripgrep",
        "binaryName": "rg",
        "systemBinaryNames": ["rg"],
    },
}


def _is_offline_mode_enabled() -> bool:
    value = os.environ.get("OPENCLAW_OFFLINE", "")
    return value in ("1", "true", "True", "yes", "YES")


def _command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(cmd) is not None


def get_tool_path(tool: ToolName) -> str | None:
    """Get the path to a tool (system-wide or in our tools dir)."""
    config = _TOOL_CONFIGS.get(tool)
    if not config:
        return None

    # Check system PATH
    for system_binary_name in config.get("systemBinaryNames", [config["binaryName"]]):
        if _command_exists(system_binary_name):
            return system_binary_name

    return None


async def ensure_tool(tool: ToolName, silent: bool = False) -> str | None:
    """Ensure a tool is available, downloading if necessary.

    Returns the path to the tool, or None if unavailable.
    """
    existing_path = get_tool_path(tool)
    if existing_path:
        return existing_path

    config = _TOOL_CONFIGS.get(tool)
    if not config:
        return None

    if _is_offline_mode_enabled():
        if not silent:
            print(f"{config['name']} not found. Offline mode enabled, skipping download.")
        return None

    # Download logic deferred — requires HTTP fetch + archive extraction
    if not silent:
        print(f"{config['name']} not found. Auto-download not yet implemented in Python port.")
    return None
