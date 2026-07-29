from __future__ import annotations

import re

_CONFIG_SET_RE = re.compile(r"^([a-zA-Z0-9_.-]+)=(.*)$")


def parse_config_set_arg(arg: str) -> tuple[str, str] | None:
    m = _CONFIG_SET_RE.match(arg)
    if not m:
        return None
    return m.group(1), m.group(2)


def parse_config_set_args(args: list[str]) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for arg in args:
        parsed = parse_config_set_arg(arg)
        if parsed:
            results.append(parsed)
    return results
