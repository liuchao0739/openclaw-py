from __future__ import annotations

import re

from openclaw.packages.normalization_core import normalize_optional_lowercase_string


def parse_json_output_mode(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_optional_lowercase_string(value)
    if normalized in ("json", "text", "pretty"):
        return normalized
    return None


def is_json_output_mode(value: str | None) -> bool:
    return parse_json_output_mode(value) == "json"


def has_json_flag(argv: list[str]) -> bool:
    return any(arg == "--json" or arg.startswith("--json=") for arg in argv)


def resolve_json_output_mode(argv: list[str], env: dict | None = None) -> str | None:
    import os

    if has_json_flag(argv):
        return "json"
    env_map = env if env is not None else dict(os.environ)
    return parse_json_output_mode(env_map.get("OPENCLAW_OUTPUT"))
