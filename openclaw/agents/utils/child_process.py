"""Child process helpers for agent tool execution.

Provides spawn/exec wrappers with timeout and signal support.
The full implementation is deferred; this stub provides the interface.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def run_command(
    command: str,
    args: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout_ms: int | None = None,
    input_text: str | None = None,
) -> dict[str, Any]:
    """Run a command asynchronously and return stdout/stderr/exitCode."""
    try:
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_text is not None else None,
            cwd=cwd,
            env=env,
        )

        stdin_data = input_text.encode() if input_text else None
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data),
                timeout=timeout_ms / 1000.0 if timeout_ms else None,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout_ms}ms",
                "exitCode": -1,
                "timedOut": True,
            }

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exitCode": proc.returncode or 0,
            "timedOut": False,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"Command not found: {command}",
            "exitCode": -1,
            "timedOut": False,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1,
            "timedOut": False,
        }
