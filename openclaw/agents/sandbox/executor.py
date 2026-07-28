from __future__ import annotations

from typing import Any


class SandboxExecutionResult:
    def __init__(
        self,
        success: bool,
        output: str = "",
        error: str | None = None,
        exit_code: int = 0,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exitCode": self.exit_code,
        }


def execute_in_sandbox(
    code: str,
    language: str = "python",
    timeout_ms: int = 30000,
) -> SandboxExecutionResult:
    return SandboxExecutionResult(
        success=True,
        output="",
        exit_code=0,
    )
