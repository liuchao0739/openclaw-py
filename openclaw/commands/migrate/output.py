from __future__ import annotations

import json
from typing import Any


def _output_result(result: dict[str, Any], json_output: bool = False, runtime: dict[str, Any] | None = None) -> None:
    rt = runtime or {}
    if json_output or rt.get("writeJson"):
        if rt.get("writeJson"):
            rt["writeJson"](rt, result)
        return
    if rt.get("log"):
        rt["log"](json.dumps(result, indent=2))


def _output_summary(lines: list[str], runtime: dict[str, Any] | None = None) -> None:
    rt = runtime or {}
    if rt.get("log"):
        for line in lines:
            rt["log"](line)


async def output_migration_result(
    result: dict[str, Any],
    json_output: bool = False,
    runtime: dict[str, Any] | None = None,
) -> None:
    _output_result(result, json_output, runtime)


async def output_migration_summary(
    summary: list[str],
    runtime: dict[str, Any] | None = None,
) -> None:
    _output_summary(summary, runtime)
