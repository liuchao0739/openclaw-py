from __future__ import annotations

from typing import Any


def build_agent_runtime_id(
    provider: str,
    model: str,
    profile_id: str | None = None,
) -> str:
    if profile_id:
        return f"{provider}:{model}:{profile_id}"
    return f"{provider}:{model}"


def parse_agent_runtime_id(runtime_id: str) -> dict[str, str] | None:
    parts = runtime_id.split(":")
    if len(parts) < 2:
        return None
    result = {"provider": parts[0], "model": parts[1]}
    if len(parts) > 2:
        result["profileId"] = parts[2]
    return result
