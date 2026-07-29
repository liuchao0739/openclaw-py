from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock


def create_cli_runtime_mock(options: dict | None = None) -> dict:
    opts = options or {}
    exit_prefix = opts.get("exitPrefix", "__exit__")
    runtime_logs: list[str] = []
    runtime_errors: list[str] = []

    def _stringify(args: tuple) -> str:
        return " ".join(str(a) for a in args)

    default_runtime = MagicMock()
    default_runtime.log = MagicMock(side_effect=lambda *args: runtime_logs.append(_stringify(args)))
    default_runtime.error = MagicMock(side_effect=lambda *args: runtime_errors.append(_stringify(args)))
    default_runtime.writeStdout = MagicMock(
        side_effect=lambda value: default_runtime.log(
            value[:-1] if value.endswith("\n") else value
        )
    )
    default_runtime.writeJson = MagicMock(
        side_effect=lambda value, space=2: default_runtime.log(
            json.dumps(value, indent=space if space > 0 else None)
        )
    )
    default_runtime.exit = MagicMock(
        side_effect=lambda code=0: (_ for _ in ()).throw(RuntimeError(f"{exit_prefix}:{code}"))
    )

    return {
        "runtimeLogs": runtime_logs,
        "runtimeErrors": runtime_errors,
        "defaultRuntime": default_runtime,
    }
