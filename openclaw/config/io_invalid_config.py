from __future__ import annotations

from typing import Any


class ConfigRuntimeRefreshError(Exception):
    pass


def create_invalid_config_error(
    config_path: str,
    details: str,
) -> Exception:
    return ValueError(f"Invalid config at {config_path}: {details}")


def format_invalid_config_details(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "Unknown validation error"
    parts = []
    for issue in issues:
        path = issue.get("path", "unknown")
        message = issue.get("message", "Unknown error")
        allowed = issue.get("allowedValues")
        entry = f"  - {path}: {message}"
        if allowed:
            entry += f" (allowed: {', '.join(str(v) for v in allowed)})"
        parts.append(entry)
    return "\n".join(parts)
