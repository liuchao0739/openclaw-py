from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

from .error_utils import format_error_message


DEFAULT_WINDOWS_SYSTEM_ROOT = r"C:\Windows"


class CliCommandError(Exception):
    def __init__(self, command_summary: str, code: Optional[int], signal: Optional[str], stdout: str, stderr: str):
        if code is None:
            exit_info = f"signal {signal or 'unknown'}"
        else:
            exit_info = f"code {code}"
        message = f"{command_summary} failed ({exit_info}): {stderr or stdout}"
        super().__init__(message)
        self.name = "CliCommandError"
        self.code = code
        self.signal = signal
        self.stdout = stdout
        self.stderr = stderr


def resolve_cli_spawn_invocation(command: str, args: List[str]) -> Dict[str, Any]:
    return {
        "command": command,
        "args": args,
        "shell": False,
        "windowsHide": True,
    }


def check_qmd_binary_availability(
    command: str,
    timeout_ms: int = 2000,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    if not command:
        return {"available": False, "reason": "binary", "error": "No command configured"}

    if cwd:
        try:
            if not os.path.isdir(cwd):
                return {
                    "available": False,
                    "reason": "workspace-cwd",
                    "error": f"workspace directory is not a directory: {cwd}",
                }
        except OSError:
            return {
                "available": False,
                "reason": "workspace-cwd",
                "error": f"workspace directory unavailable: {cwd}",
            }

    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
            cwd=cwd,
        )
        return {"available": True}
    except FileNotFoundError:
        return {"available": False, "reason": "binary", "error": f"Command not found: {command}"}
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "binary", "error": f"Command timed out after {timeout_ms}ms"}
    except Exception as e:
        return {"available": False, "reason": "binary", "error": format_error_message(e)}


def run_cli_command(
    command_summary: str,
    command: str,
    args: List[str],
    cwd: str,
    env: Optional[Dict[str, str]] = None,
    timeout_ms: Optional[int] = None,
    max_output_chars: int = 100_000,
    discard_stdout: bool = False,
) -> Dict[str, str]:
    cmd = resolve_cli_spawn_invocation(command, args)

    if timeout_ms is not None:
        timeout = timeout_ms / 1000
    else:
        timeout = None

    try:
        result = subprocess.run(
            [cmd["command"]] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            shell=cmd.get("shell", False),
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if not discard_stdout and (len(stdout) > max_output_chars or len(stderr) > max_output_chars):
            raise CliCommandError(
                command_summary,
                result.returncode,
                None,
                stdout[-max_output_chars:],
                stderr[-max_output_chars:],
            )

        if result.returncode == 0:
            return {"stdout": stdout, "stderr": stderr}
        else:
            raise CliCommandError(
                command_summary,
                result.returncode,
                None,
                stdout,
                stderr,
            )
    except subprocess.TimeoutExpired as e:
        raise CliCommandError(
            command_summary,
            None,
            "timeout",
            e.stdout or "",
            e.stderr or "",
        )
    except CliCommandError:
        raise
    except Exception as e:
        raise CliCommandError(command_summary, None, None, "", format_error_message(e))
