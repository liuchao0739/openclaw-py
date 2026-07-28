from __future__ import annotations

from typing import TypedDict

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty


class ParsedClawHubPluginSpec(TypedDict):
    name: str
    version: str | None


def parse_clawhub_plugin_spec(raw: str) -> ParsedClawHubPluginSpec | None:
    trimmed = raw.strip()
    if not normalize_lowercase_string_or_empty(trimmed).startswith("clawhub:"):
        return None
    spec = trimmed[len("clawhub:"):].strip()
    if not spec:
        return None
    at_index = spec.rfind("@")
    if at_index <= 0:
        return {"name": spec, "version": None}
    if at_index >= len(spec) - 1:
        return None
    name = spec[:at_index].strip()
    version = spec[at_index + 1:].strip()
    if not name or not version:
        return None
    return {"name": name, "version": version}


__all__ = [
    "ParsedClawHubPluginSpec",
    "parse_clawhub_plugin_spec",
]
